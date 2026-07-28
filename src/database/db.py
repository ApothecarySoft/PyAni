import threading
import ladybug as lb 


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
        """Initializes the embedded LadybugDB engine in a local directory."""
        if self._db is None:
            with self._lock:
                if self._db is None:
                    # Initialize Ladybug database and connection mapping
                    self._db = lb.Database(db_path)
                    self._conn = lb.Connection(self._db)

                    # Establish tables safely
                    self._verify_schema()
                    print(f"✅ Centralized LadybugDB initialized at: {db_path}")

    def _verify_schema(self):
        self._conn.execute(
            """
            CREATE NODE TABLE IF NOT EXISTS User (
                id INT64 PRIMARY KEY,
                username STRING,
                last_chunk_count INT64,
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
                id INT64,
                type STRING,
                name STRING,
                last_updated TIMESTAMP,
                PRIMARY KEY (id, name, type)
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
                strength_norm DOUBLE,
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
                FROM User TO User,
                is_mutual BOOLEAN
            )
        """
        )

    def query(self, cypher: str, parameters: dict = None):
        """Executes Cypher code locally and maps column outputs to dictionary outputs."""
        if not self._conn:
            raise RuntimeError("LadybugManager is not initialized.")

        params = parameters or {}
        query_result = self._conn.execute(cypher, params)

        records = []
        column_names = query_result.get_column_names()

        # Pull row configurations sequentially out of the local processing engine
        while query_result.has_next():
            row = query_result.get_next()
            records.append(dict(zip(column_names, row)))

        return records

    def close(self):
        """Cleans up internal connection pointers on application termination."""
        if self._db:
            with self._lock:
                if self._db:
                    self._conn = None
                    self._db = None
                    print("🛑 Centralized LadybugDB instance closed.")
