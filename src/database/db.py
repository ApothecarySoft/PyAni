import threading

import ladybug as lb

from recommender.utils import get_english_title_or_user_preferred


def _parameter_string_from_parameter(prefix, parameter):
    return f"{prefix}.{parameter} = ${parameter}"


def _set_string_from_parameters(prefix, parameters):
    return {', '.join(_parameter_string_from_parameter(prefix, p) for p in parameters.keys())}


def _generate_prop_id(prop):
    return f"{prop['type']}{prop['name']}"


class LadybugManager:
    _instance = None
    _lock = threading.Lock()

    MEDIA_FRESHOLD_DAYS: int = 7
    USER_FRESHOLD_DAYS: int = 1
    PROPERTY_FRESHOLD_DAYS: int = 30

    def __init__(self):
        self._db = None
        self._conn = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(LadybugManager, cls).__new__(cls)
                    cls._instance._db = None
                    cls._instance._conn = None
        return cls._instance

    def initialize(self, db_path: str = "./app_graph_data"):
        if self._db is None:
            if self._db is None:
                self._db = lb.Database(db_path)
                self._conn = lb.Connection(self._db)

                self._create_tables()
                print(f"✅ Centralized LadybugDB initialized at: {db_path}")

    def _safe_execute(self, query, parameters = None):
        with self._lock:
            return self._conn.execute(query, parameters)

    def _is_node_fresh(
        self, node_table: str, node_id, freshold: int
    ):  # freshold = freshness threshold
        query = f"""
            MATCH (n:{node_table} {{id: $node_id}})
            RETURN n.last_updated < datetime() - duration({{days: $freshold}}) AS is_expired
        """

        return self._execute_get_first_or_default(
            query, {"node_id": node_id, "freshold": freshold}, False
        )

    def _execute_get_first_or_default(self, query, parameters, default):
        result = self._safe_execute(query, parameters).rows_as_dict()
        if result.has_next():
            return result.get_next()

        return default

    def is_user_fresh(self, username: str):
        return self._is_node_fresh("User", username, self.USER_FRESHOLD_DAYS)

    def is_media_fresh(self, media_id):
        return self._is_node_fresh("Media", media_id, self.MEDIA_FRESHOLD_DAYS)

    def is_property_fresh(self, prop_id):
        return self._is_node_fresh("Property", prop_id, self.PROPERTY_FRESHOLD_DAYS)

    def _create_or_update_node(self, node_table, node_id, parameters):
        prefix = "a"
        set_string = _set_string_from_parameters(prefix, parameters)
        query = f"""
            MERGE ({prefix}:{node_table} {{id: {node_id}}})
            ON CREATE SET {set_string}, {prefix}.last_updated = datetime()
            ON MATCH SET {set_string}, {prefix}.last_updated = datetime()
        """
        parameters["id"] = node_id
        self._safe_execute(query, parameters)

    def _create_or_update_rel(
        self, rel_table, rel_from, rel_to, id_from, id_to, parameters
    ):
        _from = "a"
        _to = "b"
        _rel = "r"
        set_string = _set_string_from_parameters(_rel, parameters)
        query = f"""
            MATCH ({_from}:{rel_from} {{id: {id_from}}}), ({_to}:{rel_to} {{id: {id_to}}})
            MERGE ({_from})-[{_rel}:{rel_table}]->({_to})
            ON CREATE SET {set_string}
            ON MATCH SET {set_string}
        """
        self._safe_execute(query, parameters)

    def create_or_update_media(self, media):
        parameters = {
            "title": get_english_title_or_user_preferred(media["title"]),
            "type": media["type"],
            "format": media["format"],
            "mean_score": media["meanScore"],
            "popularity": media["popularity"],
            "start_year": media["startDate"]["year"],
            "cover_url": media["coverImage"]["medium"],
        }
        self._create_or_update_node("Media", media["id"], parameters)

    def create_or_update_user(self, user):
        parameters = {"username": user["username"], "mean_score": user["meanScore"]}
        self._create_or_update_node("User", user["id"], parameters)

    def create_or_update_property(self, prop):
        parameters = {
            "type": prop["type"],
            "name": prop["name"],
        }
        self._create_or_update_node("Property", _generate_prop_id(prop), parameters)

    def create_or_update_user_media(self, user_id, media_id, score, status):
        parameters = {
            "score": score,
            "status": status,
        }
        self._create_or_update_rel(
            "UserMedia", "User", "Media", user_id, media_id, parameters
        )

    def create_or_update_user_property(self, user_id, prop, strength):
        parameters = {
            "strength": strength,
        }
        self._create_or_update_rel(
            "UserProperty",
            "User",
            "Property",
            user_id,
            _generate_prop_id(prop),
            parameters,
        )

    def create_or_update_media_property(self, media_id, prop, strength):
        parameters = {
            "strength": strength,
        }
        self._create_or_update_rel(
            "MediaProperty",
            "Media",
            "Property",
            media_id,
            _generate_prop_id(prop),
            parameters,
        )

    def create_or_update_rec(
        self, from_media_id, to_media_id, strength_raw, strength_norm
    ):
        parameters = {
            "strength_raw": strength_raw,
            "strength_norm": strength_norm,
        }
        self._create_or_update_rel(
            "Rec", "Media", "Media", from_media_id, to_media_id, parameters
        )

    def create_or_update_relation(self, from_media_id, to_media_id, relation_type):
        parameters = {
            "type": relation_type,
        }
        self._create_or_update_rel(
            "Relation", "Media", "Media", from_media_id, to_media_id, parameters
        )

    def create_or_update_follows(self, from_user_id, to_user_id):
        self._create_or_update_rel(
            "Follows", "User", "User", from_user_id, to_user_id, {}
        )

    def _create_tables(self):
        self._safe_execute(
            """
            CREATE NODE TABLE IF NOT EXISTS User (
                id STRING PRIMARY KEY,
                mean_score DOUBLE,
                last_updated TIMESTAMP
            )
        """ ## id is username
        )
        self._safe_execute(
            """
            CREATE NODE TABLE IF NOT EXISTS Media (
                id INT64 PRIMARY KEY,
                title STRING,
                type STRING,
                format STRING,
                mean_score INT64,
                popularity INT64,
                start_year INT64,
                last_updated TIMESTAMP,
                cover_url STRING
            )
        """
        )
        self._safe_execute(
            """
            CREATE NODE TABLE IF NOT EXISTS Property (
                id STRING PRIMARY KEY,
                type STRING,
                name STRING,
                last_updated TIMESTAMP
            )
        """
        )
        self._safe_execute(
            """
            CREATE REL TABLE IF NOT EXISTS UserMedia (
                FROM User TO Media,
                score INT64,
                status STRING
            )
        """
        )
        self._safe_execute(
            """
            CREATE REL TABLE IF NOT EXISTS UserProperty (
                FROM User TO Property,
                strength DOUBLE
            )
        """
        )
        self._safe_execute(
            """
            CREATE REL TABLE IF NOT EXISTS MediaProperty (
                FROM Media TO Property,
                strength DOUBLE
            )
        """
        )
        self._safe_execute(
            """
            CREATE REL TABLE IF NOT EXISTS Rec (
                FROM Media TO Media,
                strength_raw INT64,
                strength_norm DOUBLE
            )
        """
        )
        self._safe_execute(
            """
            CREATE REL TABLE IF NOT EXISTS Relation (
                FROM Media TO Media,
                type STRING
            )
        """
        )
        self._safe_execute(
            """
            CREATE REL TABLE IF NOT EXISTS Follows (
                FROM User TO User
            )
        """
        )

    def close(self):
        """Cleans up internal connection pointers on application termination."""
        if self._db:
            with self._lock:
                if self._db:
                    self._conn = None
                    self._db = None
                    print("🛑 Centralized LadybugDB instance closed.")
