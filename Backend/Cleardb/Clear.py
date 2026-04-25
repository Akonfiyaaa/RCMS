from Backend.database import complaints_collection

def clear_database():
    result = complaints_collection.delete_many({})
    print(f"Deleted {result.deleted_count} documents.")

if __name__ == "__main__":
    clear_database()