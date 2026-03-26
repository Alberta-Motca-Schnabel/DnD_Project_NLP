import os
from dotenv import load_dotenv

load_dotenv()

URI = os.getenv("NEO4J_URI")
USERNAME = os.getenv("NEO4J_USERNAME")
PASSWORD = os.getenv("NEO4J_PASSWORD")

# file path
FILES = {
    "2014": {
        "classes": "2014/5e-SRD-Classes.json",
        "subclasses": "2014/5e-SRD-Subclasses.json",
        "spells": "2014/5e-SRD-Spells.json",
        "races": "2014/5e-SRD-Races.json",
        "subraces": "2014/5e-SRD-Subraces.json",
        "ability_scores": "2014/5e-SRD-Ability-Scores.json",
        "backgrounds": "2014/5e-SRD-Backgrounds.json",
        "equipment": "2014/5e-SRD-Equipment.json",
        "feats": "2014/5e-SRD-Feats.json",
        "traits": "2014/5e-SRD-Traits.json",
        "languages": "2014/5e-SRD-Languages.json",
        "alignments": "2014/5e-SRD-Alignments.json",
        "magic_items": "2014/5e-SRD-Magic-Items.json",
        "magic_schools": "2014/5e-SRD-Magic-Schools.json",
        "proficiencies": "2014/5e-SRD-Proficiencies.json",
        "levels": "2014/5e-SRD-Levels.json",
        "features": "2014/5e-SRD-Features.json",
        # Integrated
        "Alignments_Integrated": "5e-SRD-Alignments_Integrated.json",
        "Backgrounds_Integrated": "5e-SRD-Backgrounds_Integrated.json",
        "Features_Integrated": "5e-SRD-Features_Integrated.json",
        "Subclasses_Integrated": "5e-SRD-Subclasses_Integrated.json",
    },
    "2024": {
        "races": "2024/5e-SRD-Species.json",
        "subraces": "2024/5e-SRD-Subspecies.json",
        "ability_scores": "2024/5e-SRD-Ability-Scores.json",
        "backgrounds": "2024/5e-SRD-Backgrounds.json",
        "equipment": "2024/5e-SRD-Equipment.json",
        "feats": "2024/5e-SRD-Feats.json",
        "traits": "2024/5e-SRD-Traits.json",
        "languages": "2024/5e-SRD-Languages.json",
        "alignments": "2024/5e-SRD-Alignments.json",
        "magic_schools": "2024/5e-SRD-Magic-Schools.json",
        "proficiencies": "2024/5e-SRD-Proficiencies.json",
        "skills": "2024/5e-SRD-Skills.json",
        # Integrated
        "Backgrounds_Integrated": "5e-SRD-Backgrounds_Integrated.json",
        "Features_Integrated": "5e-SRD-Features_Integrated.json",
        "Subclasses_Integrated": "5e-SRD-Subclasses_Integrated.json",
        "Species_Integrated": "5e-SRD-Species_Integrated.json",
        "Spells_Integrated": "5e-SRD-Spells_Integrated.json",
        "Feats_Integrated": "5e-SRD-Feats_Integrated.json",
        "Traits_Integrated": "5e-SRD-Traits_Integrated.json",
    }
}