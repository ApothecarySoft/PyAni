import threading
import ladybug as lb

from recommender.utils import get_english_title_or_user_preferred, get_today_date_stamp


def _parameter_string_from_parameter(prefix, parameter):
    return f"{prefix}.{parameter} = ${parameter}"


def _generate_prop_id(prop):
    return f"{prop['type']}{prop['name']}"


class LadybugManager:
    _instance = None
    _lock = threading.Lock()

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
            with self._lock:
                if self._db is None:
                    self._db = lb.Database(db_path)
                    self._conn = lb.Connection(self._db)

                    self._create_tables()
                    print(f"✅ Centralized LadybugDB initialized at: {db_path}")

    def _create_or_update_node(self, node_table, node_id, parameters):
        prefix = 'a'
        query = f"""
            MERGE ({prefix}:{node_table} {{id: {node_id}}})
            ON CREATE SET {', '.join(_parameter_string_from_parameter(prefix, p) for p in parameters.keys())}, {prefix}.last_updated = current_timestamp()
            ON MATCH SET {', '.join(_parameter_string_from_parameter(prefix, p) for p in parameters.keys())}, {prefix}.last_updated = current_timestamp()
        """
        parameters['id'] = node_id
        self._conn.execute(query, parameters)

    def _create_or_update_rel(self, rel_table, rel_from, rel_to, id_from, id_to, parameters):
        _from = 'a'
        _to = 'b'
        _rel = 'r'
        query = f"""
            MATCH ({_from}:{rel_from} {{id: {id_from}}}), ({_to}:{rel_to} {{id: {id_to}}})
            MERGE ({_from})-[{_rel}:{rel_table}]->({_to})
            ON CREATE SET {', '.join(_parameter_string_from_parameter(_rel, p) for p in parameters.keys())}
            ON MATCH SET {', '.join(_parameter_string_from_parameter(_rel, p) for p in parameters.keys())}
        """
        self._conn.execute(query, parameters)

    def create_or_update_media(self, media):
        parameters = {
            "title": get_english_title_or_user_preferred(media['title']),
            "type": media['type'],
            "format": media['format'],
            "mean_score": media['meanScore'],
            "popularity": media['popularity'],
            "start_year": media['startDate']['year'],
            "cover_url": media['coverImage']['medium']
        }
        self._create_or_update_node("Media", media['id'], parameters)

    def create_or_update_user(self, user):
        parameters = {
            'username': user['username'],
            'mean_score': user['meanScore']
        }
        self._create_or_update_node("User", user['id'], parameters)

    def create_or_update_property(self, prop):
        parameters = {
            'type': prop['type'],
            'name': prop['name'],
        }
        self._create_or_update_node("Property", _generate_prop_id(prop), parameters)

    def create_or_update_user_media(self, user_id, media_id, score, status):
        parameters = {
            'score': score,
            'status': status,
        }
        self._create_or_update_rel("UserMedia", "User", "Media", user_id, media_id, parameters)

    def create_or_update_user_property(self, user_id, prop, strength):
        parameters = {
            'strength': strength,
        }
        self._create_or_update_rel("UserProperty", "User", "Property", user_id, _generate_prop_id(prop), parameters)

    def create_or_update_media_property(self, media_id, prop, strength):
        parameters = {
            'strength': strength,
        }
        self._create_or_update_rel("MediaProperty", "Media", "Property", media_id, _generate_prop_id(prop), parameters)

    def create_or_update_rec(self, from_media_id, to_media_id, strength_raw, strength_norm):
        parameters = {
            'strength_raw': strength_raw,
            'strength_norm': strength_norm,
        }
        self._create_or_update_rel("Rec", "Media", "Media", from_media_id, to_media_id, parameters)

    def create_or_update_relation(self, from_media_id, to_media_id, relation_type):
        parameters = {
            'type': relation_type,
        }
        self._create_or_update_rel("Relation", "Media", "Media", from_media_id, to_media_id, parameters)

    def create_or_update_follows(self, from_user_id, to_user_id):
        self._create_or_update_rel("Follows", "User", "User", from_user_id, to_user_id, {})

    def _create_tables(self):
        self._conn.execute(
            """
            CREATE NODE TABLE IF NOT EXISTS User (
                id INT64 PRIMARY KEY,
                username STRING,
                mean_score DOUBLE,
                last_updated TIMESTAMP
            )
        """
        )
        self._conn.execute(
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
        self._conn.execute(
            """
            CREATE NODE TABLE IF NOT EXISTS Property (
                id STRING PRIMARY KEY,
                type STRING,
                name STRING,
                last_updated TIMESTAMP
            )
        """
        )
        self._conn.execute(
            """
            CREATE REL TABLE IF NOT EXISTS UserMedia (
                FROM User TO Media,
                score INT64,
                status STRING
            )
        """
        )
        self._conn.execute(
            """
            CREATE REL TABLE IF NOT EXISTS UserProperty (
                FROM User TO Property,
                strength DOUBLE
            )
        """
        )
        self._conn.execute(
            """
            CREATE REL TABLE IF NOT EXISTS MediaProperty (
                FROM Media TO Property,
                strength DOUBLE
            )
        """
        )
        self._conn.execute(
            """
            CREATE REL TABLE IF NOT EXISTS Rec (
                FROM Media TO Media,
                strength_raw INT64,
                strength_norm DOUBLE
            )
        """
        )
        self._conn.execute(
            """
            CREATE REL TABLE IF NOT EXISTS Relation (
                FROM Media TO Media,
                type STRING
            )
        """
        )
        self._conn.execute(
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
