from neo4j import GraphDatabase

class Neo4jConnector:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    # ==========================================
    #  CYPHER QUERIES 
    # ==========================================
    @staticmethod
    def _merge_node(tx, label, index, name, version, extra_props=None):
        query = f"MERGE (n:{label} {{index: $index, srd_version: $version}}) SET n.name = $name"
        if extra_props:
            for key in extra_props.keys():
                query += f", n.{key} = ${key}"
        
        params = {"index": index, "name": name, "version": version}
        if extra_props:
            params.update(extra_props)
        tx.run(query, **params)

    @staticmethod
    def _create_relation(tx, label1, index1, label2, index2, rel_type, version):
        query = f"""
        MATCH (a:{label1} {{index: $index1, srd_version: $version}})
        MATCH (b:{label2} {{index: $index2, srd_version: $version}})
        MERGE (a)-[:{rel_type}]->(b)
        """
        tx.run(query, index1=index1, index2=index2, version=version)

    @staticmethod
    def _create_relation_with_prop(tx, label1, index1, label2, index2, rel_type, prop_name, prop_value, version):
        query = f"""
        MATCH (a:{label1} {{index: $index1, srd_version: $version}})
        MATCH (b:{label2} {{index: $index2, srd_version: $version}})
        MERGE (a)-[r:{rel_type}]->(b)
        SET r.{prop_name} = $prop_value
        """
        tx.run(query, index1=index1, index2=index2, prop_value=prop_value, version=version)

    @staticmethod
    def _set_property(tx, label, index, prop_name, prop_value, version):
        query = f"MATCH (n:{label} {{index: $index, srd_version: $version}}) SET n.{prop_name} = $prop_value"
        tx.run(query, index=index, prop_value=prop_value, version=version)