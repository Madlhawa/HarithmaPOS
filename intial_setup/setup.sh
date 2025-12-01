# installing rabbit MQ
    # https://www.rabbitmq.com/docs/install-debian#apt-quick-start-cloudsmith

# deploying the application
    curl -o deploy.sh https://raw.githubusercontent.com/Madlhawa/HarithmaPOS/main/intial_setup/deploy.sh
    chmod +x deploy.sh
    ./deploy.sh

# installing postgresql server
    sudo apt update
    sudo apt install postgresql postgresql-contrib
    sudo -i -u postgres
        psql
            createuser --interactive
    vi /etc/postgresql/14/main/pg_hba.conf
    vi /etc/postgresql/14/main/postgresql.conf
    systemctl restart postgresql
    systemctl status postgresql

# intalling superset
    # https://github.com/shantanukhond/YT-Assets/tree/main/Superset/installation

# other commands
    python -m flask shell
    from harithmapos import db
    db.create_all()

# migrating db
    set FLASK_APP=harithmapos
    flask db init #only first time
    flask db migrate
    flask db upgrade

# resetting db
    flask db reset
    flask db init
    flask db migrate
    flask db upgrade

    # python -c "from harithmapos import create_app, db; app = create_app(); app.app_context().push(); db.drop_all(); db.create_all(); print('Database recreated')"