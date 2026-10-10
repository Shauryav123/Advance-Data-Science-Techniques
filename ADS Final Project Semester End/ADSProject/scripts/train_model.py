import db
from analysis import train_and_store


if __name__ == "__main__":
    db.seed_from_csv()
    print(train_and_store())
