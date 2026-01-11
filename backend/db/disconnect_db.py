from backend.db.session import engine

def disconnect_db() -> None:
    # Close pooled connections
    engine.dispose()