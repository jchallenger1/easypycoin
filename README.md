
# Easypycoin
Easypycoin is a simple implementation of a cryptocurrency

## Getting Started
These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. 

### Prerequisites
Python3 and pip3 is required, and can be installed via:
```
sudo apt install python3.6
sudo apt install python3-pip
```
### Installing - Getting a development environment running
Either download and unzip this repository via the top right or by cloning the repository first:
```
git clone https://github.com/Grandduchy/easypycoin
cd easypycoin
```
Create and run a virtual environment, otherwise requirements of this project will be installed globally on your computer
```
python3 -m venv easypycoin_env
easypycoin_env/bin/activate
```
Install the requirements for this project
```
pip install -r requirements.txt
```
Run the server
```
python3 coinbase.py
```
The server is now running, you can view the web interface at http://127.0.0.1:5000/

## Built With

* [Flask](https://flask.palletsprojects.com) - The web framework used
* [JQuery](https://jquery.com/) - Javascript Library used
* [Bootstrap](https://getbootstrap.com/) - CSS Library used
* [Flask-SQLAlchemy](https://flask-sqlalchemy.palletsprojects.com) - Object relational mapper used with [SQLite](https://sqlite.org/index.html)
* [Cryptography](https://cryptography.io/en/latest/) - Crypto library used
## Authors

* **Joshua Challenger** - *Complete Project* - [Grandduchy](https://github.com/Grandduchy)
## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details
