from database import Neo4jConnector

class DnDKnowledgeGraph(Neo4jConnector):
    
    # Loaders

    def load_classes(self, classes_data, version):
        """
        Loads D&D classes into the knowledge graph.
        Handles base stats, multiclassing prerequisites, saving throw proficiencies, 
        skill choices, and starting equipment.
        """
        # Mapping to define at which level a class unlocks its subclass
        subclass_unlock_map = {
            "cleric": 1, "sorcerer": 1, "warlock": 1,
            "druid": 2, "wizard": 2
        }
        
        # Multipliers for multiclass spell slot progression calculation
        caster_prog_map = {
            "bard": 1.0, "cleric": 1.0, "druid": 1.0, "sorcerer": 1.0, "wizard": 1.0,
            "paladin": 0.5, "ranger": 0.5,
            "warlock": -1.0, 
            "fighter": 0.0, "rogue": 0.0, "barbarian": 0.0, "monk": 0.0
        }

        # Spell preparation mechanics per class
        spellcasting_type_map = {
            "bard": "known", "ranger": "known", "sorcerer": "known", "warlock": "known",
            "cleric": "prepared", "druid": "prepared", "paladin": "prepared", "wizard": "prepared",
            "artificer": "prepared" 
        }

        with self.driver.session() as session:
            for cls in classes_data:
                class_index = cls.get("index")
                name = cls.get("name")
                hit_die = cls.get("hit_die")
                
                unlock_lvl = subclass_unlock_map.get(class_index, 3) 
                caster_prog = caster_prog_map.get(class_index, 0.0)
                
                # Create or update the main Class node
                session.execute_write(self._merge_node, "Class", class_index, name, version, {
                    "hit_die": hit_die,
                    "subclass_unlock_level": unlock_lvl,
                    "caster_progression": caster_prog,
                    "spellcasting_type": spellcasting_type_map.get(class_index, "none")
                })
                
                # Link primary spellcasting ability stat
                spellcasting = cls.get("spellcasting", {})
                spell_ability = spellcasting.get("spellcasting_ability", {}).get("index")
                if spell_ability:
                    session.execute_write(self._create_relation, "Class", class_index, "Stat", spell_ability, "USES_MAGIC_STAT", version)
                    
                # Link saving throw proficiencies
                for save in cls.get("saving_throws", []):
                    stat_index = save.get("index")
                    if stat_index:
                        session.execute_write(self._create_relation, "Class", class_index, "Stat", stat_index, "PROFICIENT_IN_SAVE", version)
                
                # Link multiclassing requirements and granted proficiencies
                multiclass = cls.get("multi_classing", {})
                for prereq in multiclass.get("prerequisites", []):
                    stat_idx = prereq.get("ability_score", {}).get("index")
                    min_score = prereq.get("minimum_score")
                    if stat_idx and min_score:
                        session.execute_write(self._create_relation_with_prop, "Class", class_index, "Stat", stat_idx, "MULTICLASS_REQUIRES", "min_score", min_score, version)
                
                for prof in multiclass.get("proficiencies", []):
                    prof_idx = prof.get("index")
                    if prof_idx:
                        session.execute_write(self._create_relation, "Class", class_index, "Proficiency", prof_idx, "MULTICLASS_GRANTS_PROFICIENCY", version)

                # Process skill and tool proficiency choices
                prof_choices = cls.get("proficiency_choices", [])
                for choice_block in prof_choices:
                    choose_count = choice_block.get("choose", 0)
                    options = choice_block.get("from", {}).get("options", [])
                    is_skill_block = False

                    for opt in options:
                        item = opt.get("item", {})
                        item_index = item.get("index", "")
                        if item_index.startswith("skill-"):
                            is_skill_block = True
                            clean_name = item.get("name", "").replace("Skill: ", "")
                            # Ensure the Skill node exists before linking
                            session.execute_write(self._merge_node, "Skill", item_index, clean_name, version)
                            session.execute_write(self._create_relation, "Class", class_index, "Skill", item_index, "CAN_CHOOSE_SKILL", version)
                    
                    # Store how many skills the player can pick from the allowed list
                    if is_skill_block:
                        session.execute_write(self._set_property, "Class", class_index, "skills_to_choose", choose_count, version)
                
                # Link starting equipment and quantities
                starting_equip = cls.get("starting_equipment", [])
                for equip in starting_equip:
                    equip_idx = equip.get("equipment", {}).get("index")
                    qty = equip.get("quantity", 1)
                    if equip_idx:
                        session.execute_write(self._create_relation_with_prop, "Class", class_index, "Equipment", equip_idx, "STARTING_EQUIPMENT", "quantity", qty, version)

    def load_subclasses(self, subclasses_data, version):
        """
        Loads subclass definitions 
        and links them to their parent Class.
        """
        with self.driver.session() as session:
            for sub in subclasses_data:
                sub_index = sub.get("index")
                sub_name = sub.get("name")
                parent_class_index = sub.get("class", {}).get("index")
                
                flavor = sub.get("subclass_flavor", "")
                desc_raw = sub.get("desc", [])
                description = "\n".join(desc_raw) if isinstance(desc_raw, list) else str(desc_raw)

                if parent_class_index:
                    session.execute_write(self._merge_node, "Subclass", sub_index, sub_name, version, {
                        "flavor": flavor,
                        "description": description
                    })
                    # Link subclass to parent class
                    session.execute_write(self._create_relation, "Class", parent_class_index, "Subclass", sub_index, "HAS_SUBCLASS", version)

    def load_spells(self, spells_data, version):
        """
        Loads spell data, including descriptions, levels, duration, and damage types.
        Links spells to the Classes/Subclasses that can learn them, and to Magic Schools.
        """
        with self.driver.session() as session:
            for spell in spells_data:
                spell_index = spell.get("index")
                spell_name = spell.get("name")
                spell_level = spell.get("level")
                
                desc = spell.get("desc", [])
                description = "\n".join(desc) if isinstance(desc, list) else str(desc)
                
                higher_lvl = spell.get("higher_level", [])
                higher_level_desc = "\n".join(higher_lvl) if isinstance(higher_lvl, list) else str(higher_lvl)

                # Create the Spell node
                session.execute_write(self._merge_node, "Spell", spell_index, spell_name, version, {
                    "level": spell_level,
                    "description": description,
                    "higher_level_description": higher_level_desc,
                    "casting_time": spell.get("casting_time"), 
                    "duration": spell.get("duration")
                })
                
                # Link to classes and subclasses that have access to this spell
                for cls in spell.get("classes", []):
                    session.execute_write(self._create_relation, "Class", cls.get("index"), "Spell", spell_index, "CAN_LEARN", version)
                
                for sub in spell.get("subclasses", []):
                    session.execute_write(self._create_relation, "Subclass", sub.get("index"), "Spell", spell_index, "CAN_LEARN", version)

                # Link to the magic school 
                school_index = spell.get("school", {}).get("index")
                if school_index:
                    session.execute_write(self._create_relation, "Spell", spell_index, "MagicSchool", school_index, "BELONGS_TO_SCHOOL", version)
                    
                # Link to specific damage types dealt by the spell
                dmg_type_idx = spell.get("damage", {}).get("damage_type", {}).get("index")
                if dmg_type_idx:
                    session.execute_write(self._merge_node, "DamageType", dmg_type_idx, dmg_type_idx.capitalize(), version)
                    session.execute_write(self._create_relation, "Spell", spell_index, "DamageType", dmg_type_idx, "DEALS_DAMAGE", version)

    def load_races(self, races_data, version):
        """
        Loads base player races storing speed, size, 
        stat bonuses, and known languages.
        """
        with self.driver.session() as session:
            for race in races_data:
                race_index = race.get("index")
                name = race.get("name")
                
                session.execute_write(self._merge_node, "Race", race_index, name, version, {
                    "speed": race.get("speed"), 
                    "size": race.get("size"),
                    "type": race.get("type", "")
                })

                # Link stat boosts
                for bonus in race.get("ability_bonuses", []):
                    stat_index = bonus.get("ability_score", {}).get("index")
                    bonus_val = bonus.get("bonus")
                    if stat_index and bonus_val:
                        session.execute_write(self._merge_node, "Stat", stat_index, stat_index.upper(), version)
                        session.execute_write(self._create_relation_with_prop, "Race", race_index, "Stat", stat_index, "HAS_BONUS", "value", bonus_val, version)

                # Link spoken languages
                for lang in race.get("languages", []):
                    lang_index = lang.get("index")
                    if lang_index:
                        session.execute_write(self._create_relation, "Race", race_index, "Language", lang_index, "SPEAKS", version)
                        
    def load_subraces(self, subraces_data, version):
        """
        Loads subraces and links them to their parent Race.
        """
        with self.driver.session() as session:
            for sub in subraces_data:
                sub_index = sub.get("index")
                name = sub.get("name")
                
                parent_race = sub.get("race") or sub.get("species")
                parent_race_index = parent_race.get("index") if parent_race else None
                
                if parent_race_index:
                    session.execute_write(self._merge_node, "Subrace", sub_index, name, version)
                    session.execute_write(self._create_relation, "Race", parent_race_index, "Subrace", sub_index, "HAS_SUBRACE", version)

                # Link specific damage resistances 
                dmg_type_data = sub.get("damage_type")
                if dmg_type_data:
                    dmg_type_idx = dmg_type_data.get("index") if isinstance(dmg_type_data, dict) else dmg_type_data
                    
                    if dmg_type_idx:
                        session.execute_write(self._merge_node, "DamageType", dmg_type_idx, dmg_type_idx.capitalize(), version)
                        session.execute_write(self._create_relation, "Subrace", sub_index, "DamageType", dmg_type_idx, "HAS_RESISTANCE", version)

                # Link additional stat boosts specific to the subrace
                for bonus in sub.get("ability_bonuses", []):
                    stat_index = bonus.get("ability_score", {}).get("index")
                    bonus_val = bonus.get("bonus")
                    if stat_index and bonus_val:
                        session.execute_write(self._create_relation_with_prop, "Subrace", sub_index, "Stat", stat_index, "HAS_BONUS", "value", bonus_val, version)

    def load_backgrounds(self, data, version):
        """
        Loads character backgrounds 
        Maps features, starting skill proficiencies, stat boosts, feats, and starting money/equipment.
        """
        with self.driver.session() as session:
            for bg in data:
                bg_index = bg.get("index")
                name = bg.get("name")
                
                bg_desc_raw = bg.get("description", bg.get("desc", []))
                bg_desc = "\n".join(bg_desc_raw) if isinstance(bg_desc_raw, list) else str(bg_desc_raw)
                
                feature_data = bg.get("feature", {})
                feature_name = feature_data.get("name", "")
                feature_desc_raw = feature_data.get("desc", [])
                feature_desc = "\n".join(feature_desc_raw) if isinstance(feature_desc_raw, list) else str(feature_desc_raw)
                
                session.execute_write(self._merge_node, "Background", bg_index, name, version, {
                    "description": bg_desc,
                    "feature_name": feature_name,
                    "feature_description": feature_desc
                })
                
                # Link granted skill proficiencies
                profs = bg.get("starting_proficiencies") or bg.get("proficiencies") or []
                for prof in profs:
                    prof_index = prof.get("index", "")
                    if prof_index.startswith("skill-"):
                        session.execute_write(self._create_relation, "Background", bg_index, "Skill", prof_index.replace("skill-", ""), "GRANTS_SKILL", version)
                
                # Link potential ability score boosts
                for stat in bg.get("ability_scores", []):
                    stat_index = stat.get("index")
                    if stat_index:
                        session.execute_write(self._create_relation, "Background", bg_index, "Stat", stat_index, "BOOSTS_STAT", version)
                
                # Link granted feats
                feat = bg.get("feat")
                if feat and feat.get("index"):
                    session.execute_write(self._create_relation, "Background", bg_index, "Feat", feat.get("index"), "GRANTS_FEAT", version)
                    
                # Link fixed starting equipment
                starting_equip = bg.get("starting_equipment", [])
                for equip in starting_equip:
                    equip_idx = equip.get("equipment", {}).get("index")
                    qty = equip.get("quantity", 1)
                    if equip_idx:
                        session.execute_write(self._create_relation_with_prop, "Background", bg_index, "Equipment", equip_idx, "STARTING_EQUIPMENT", "quantity", qty, version)
                
                # Process equipment options and starting money 
                equip_opts = bg.get("equipment_options", [])
                for opt in equip_opts:
                    options_array = opt.get("from", {}).get("options", [])
                    for sub_opt in options_array:
                        if sub_opt.get("option_type") == "multiple":
                            items = sub_opt.get("items", [])
                            for item in items:
                                if item.get("option_type") == "counted_reference":
                                    equip_idx = item.get("of", {}).get("index")
                                    qty = item.get("count", 1)
                                    if equip_idx:
                                        session.execute_write(self._create_relation_with_prop, "Background", bg_index, "Equipment", equip_idx, "STARTING_EQUIPMENT", "quantity", qty, version)
                                elif item.get("option_type") == "money":
                                    coins = item.get("count")
                                    unit = item.get("unit") # gp, sp, cp
                                    if coins:
                                        session.execute_write(self._set_property, "Background", bg_index, f"starting_money_{unit}", coins, version)

    def load_features(self, data, version):
        """
        Loads class and subclass features 
        Links features to their source and to the specific level they are acquired.
        """
        with self.driver.session() as session:
            for feat in data:
                feature_index = feat.get("index")
                name = feat.get("name")
                level = feat.get("level")
                
                desc = feat.get("desc", [])
                desc_text = "\n".join(desc) if isinstance(desc, list) else str(desc)
                description = feat.get("description", desc_text)
                
                class_index = feat.get("class", {}).get("index")
                subclass_index = feat.get("subclass", {}).get("index")
                
                source_type = "subclass" if subclass_index else "class"
                
                session.execute_write(self._merge_node, "Feature", feature_index, name, version, {
                    "level_required": level,
                    "description": description,
                    "source_type": source_type
                })
                
                # Map standard class features to the appropriate class level node
                if class_index:
                    session.execute_write(self._create_relation, "Class", class_index, "Feature", feature_index, "HAS_FEATURE", version)
                    if level is not None:
                        level_index = f"{class_index}-{level}" # e.g., rogue-3
                        session.execute_write(self._create_relation, "Level", level_index, "Feature", feature_index, "GRANTS_FEATURE", version)
                
            
                if subclass_index:
                    session.execute_write(self._create_relation, "Subclass", subclass_index, "Feature", feature_index, "HAS_FEATURE", version)
                    if level is not None:
                        query = """
                        MATCH (c:Class)-[:HAS_SUBCLASS]->(s:Subclass {index: $subclass_index, srd_version: $version})
                        MATCH (l:Level {index: c.index + '-' + toString($level), srd_version: $version})
                        MATCH (f:Feature {index: $feature_index, srd_version: $version})
                        MERGE (l)-[:GRANTS_FEATURE]->(f)
                        """
                        session.run(query, subclass_index=subclass_index, level=level, feature_index=feature_index, version=version)

    def load_traits(self, data, version):
        """
        Loads racial traits and maps them 
        to specific Races or Subraces.
        """
        with self.driver.session() as session:
            for trait in data:
                trait_index = trait.get("index")
                name = trait.get("name")
                
                desc = trait.get("desc", [])
                desc_text = "\n".join(desc) if isinstance(desc, list) else str(desc)
                description = trait.get("description", desc_text)
                
                session.execute_write(self._merge_node, "Trait", trait_index, name, version, {
                    "description": description
                })
                
                # Link to main race
                races = trait.get("races") or trait.get("species") or []
                for race in races:
                    race_index = race.get("index") if isinstance(race, dict) else race
                    if race_index:
                        session.execute_write(self._create_relation, "Race", race_index, "Trait", trait_index, "HAS_TRAIT", version)
                
                # Link to subrace
                subraces = trait.get("subraces") or trait.get("subspecies") or []
                for subrace in subraces:
                    subrace_index = subrace.get("index") if isinstance(subrace, dict) else subrace
                    if subrace_index:
                        session.execute_write(self._create_relation, "Subrace", subrace_index, "Trait", trait_index, "HAS_TRAIT", version)

    def load_ability_scores(self, data, version):
        """
        Loads the 6 core ability scores
        and links them to the skills that use them.
        """
        with self.driver.session() as session:
            for stat in data:
                stat_index = stat.get("index")
                session.execute_write(self._merge_node, "Stat", stat_index, stat.get("name"), version, {"full_name": stat.get("full_name")})
                for skill in stat.get("skills", []):
                    session.execute_write(self._create_relation, "Skill", skill.get("index"), "Stat", stat_index, "USES_STAT", version)

    def load_feats(self, data, version):
        """
        Loads feats. Handles level and ability score prerequisites.
        """
        with self.driver.session() as session:
            for feat in data:
                feat_index = feat.get("index")
                session.execute_write(self._merge_node, "Feat", feat_index, feat.get("name"), version)
                
                prereqs = feat.get("prerequisites", [])
                
                # Handle strict stat requirements
                if isinstance(prereqs, list):
                    for prereq in prereqs:
                        stat_index = prereq.get("ability_score", {}).get("index")
                        min_score = prereq.get("minimum_score")
                        if stat_index and min_score:
                            session.execute_write(self._create_relation_with_prop, "Feat", feat_index, "Stat", stat_index, "REQUIRES_STAT", "min_score", min_score, version)
                
                # Handle level requirements
                elif isinstance(prereqs, dict):
                    min_level = prereqs.get("minimum_level")
                    if min_level:
                        session.execute_write(self._set_property, "Feat", feat_index, "min_level", min_level, version)
                
                # Handle OR logic for prerequisites
                prereq_opts = feat.get("prerequisite_options", {})
                if isinstance(prereq_opts, dict) and prereq_opts.get("type") == "ability-scores":
                    options = prereq_opts.get("from", {}).get("options", [])
                    for opt in options:
                        stat_index = opt.get("item", {}).get("index")
                        if stat_index:
                            session.execute_write(self._create_relation_with_prop, "Feat", feat_index, "Stat", stat_index, "REQUIRES_STAT", "min_score", 13, version)

    def load_languages(self, data, version):
        """
        Loads languages, categorizing them by type 
        """
        with self.driver.session() as session:
            for lang in data:
                session.execute_write(self._merge_node, "Language", lang.get("index"), lang.get("name"), version, {"type": lang.get("type"), "script": lang.get("script")})

    def load_alignments(self, data, version):
        """
        Loads alignments 
        """
        with self.driver.session() as session:
            for al in data:
                session.execute_write(self._merge_node, "Alignment", al.get("index"), al.get("name"), version, {"abbreviation": al.get("abbreviation")})

    def load_magic_schools(self, data, version):
        """
        Loads the schools of magic
        """
        with self.driver.session() as session:
            for ms in data:
                session.execute_write(self._merge_node, "MagicSchool", ms.get("index"), ms.get("name"), version)

    def load_magic_items(self, data, version):
        """
        Loads magic items 
        """
        with self.driver.session() as session:
            for mi in data:
                session.execute_write(self._merge_node, "MagicItem", mi.get("index"), mi.get("name"), version, {"rarity": mi.get("rarity", {}).get("name")})

    def load_proficiencies(self, data, version):
        """
        Loads generic proficiencies 
        Links them to the classes and races that receive them natively.
        """
        with self.driver.session() as session:
            for prof in data:
                prof_index = prof.get("index")
                session.execute_write(self._merge_node, "Proficiency", prof_index, prof.get("name"), version, {"type": prof.get("type")})
                
                for cls in prof.get("classes", []):
                    session.execute_write(self._create_relation, "Class", cls.get("index"), "Proficiency", prof_index, "HAS_PROFICIENCY", version)
                
                for race in prof.get("races", []):
                    session.execute_write(self._create_relation, "Race", race.get("index"), "Proficiency", prof_index, "RACE_GRANTS_PROFICIENCY", version)

    def load_levels(self, data, version):
        """
        Constructs the leveling timeline for classes. Maps proficiency bonuses,
        Ability Score Improvements, spell slots, and unique class resources
        to specific character levels.
        """
        with self.driver.session() as session:
            for lvl in data:
                lvl_index = lvl.get("index") 
                class_index = lvl.get("class", {}).get("index")
                
                if class_index:
                    asi_bonus = lvl.get("ability_score_bonuses", 0)
                    
                    lvl_props = {
                        "level_num": lvl.get("level"),
                        "prof_bonus": lvl.get("prof_bonus"),
                        "ability_score_bonuses": asi_bonus,
                        "grants_feat_or_asi": True if asi_bonus > 0 else False
                    }
                    
                    # Dynamically capture unique class-scaling attributes 
                    class_specific = lvl.get("class_specific", {})
                    if class_specific:
                        for key, value in class_specific.items():
                            if isinstance(value, (int, float, str, bool)):
                                lvl_props[f"class_spec_{key}"] = value

                    # Map out spellcasting progression 
                    sc_data = lvl.get("spellcasting", {})
                    if sc_data:
                        if "spells_known" in sc_data:
                            lvl_props["spells_known"] = sc_data["spells_known"]
                        if "cantrips_known" in sc_data:
                            lvl_props["cantrips_known"] = sc_data["cantrips_known"]
                        # Loop through spell slot levels 1-9
                        for i in range(1, 10):
                            slot_key = f"spell_slots_level_{i}"
                            if slot_key in sc_data:
                                lvl_props[slot_key] = sc_data[slot_key]

                    session.execute_write(self._merge_node, "Level", lvl_index, lvl_index, version, lvl_props)
                    session.execute_write(self._create_relation, "Class", class_index, "Level", lvl_index, "HAS_LEVEL", version)

    def load_equipment(self, data, version):
        """
        Loads adventuring gear and weapons. Associates weapons with their 
        damage dice, specific damage types, and weapon properties
        """
        with self.driver.session() as session:
            for item in data:
                cat = item.get("equipment_category", {}).get("index")
                
                if cat == "weapon":
                    props_list = [p.get("index") for p in item.get("properties", [])]
                    
                    session.execute_write(self._merge_node, "Weapon:Equipment", item.get("index"), item.get("name"), version, {
                        "category": item.get("weapon_category"),
                        "damage": item.get("damage", {}).get("damage_dice", ""),
                        "properties": props_list
                    })
                    
                    # Link to the specific damage type node 
                    dmg_type_idx = item.get("damage", {}).get("damage_type", {}).get("index")
                    if dmg_type_idx:
                        session.execute_write(self._merge_node, "DamageType", dmg_type_idx, dmg_type_idx.capitalize(), version)
                        session.execute_write(self._create_relation, "Weapon", item.get("index"), "DamageType", dmg_type_idx, "DEALS_DAMAGE", version)

    def load_skills(self, data, version):
        """
        Loads skill definitions and connects them 
        to the Ability Score they inherently rely on.
        """
        with self.driver.session() as session:
            for skill in data:
                skill_index = skill.get("index")
                name = skill.get("name")
                
                desc = skill.get("desc", [])
                description = skill.get("description", desc[0] if desc else "")
                
                session.execute_write(self._merge_node, "Skill", skill_index, name, version, {"description": description})
                
                # Link skill to its base ability score
                stat_index = skill.get("ability_score", {}).get("index")
                if stat_index:
                    session.execute_write(self._create_relation, "Skill", skill_index, "Stat", stat_index, "USES_STAT", version)