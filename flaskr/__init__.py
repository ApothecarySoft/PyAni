import os

from flask import Flask, render_template, request


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'flaskr.sqlite'),
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # a simple page that says hello
    @app.route('/')
    def home():
        return render_template('index.html')
    
    @app.route('/results', methods=["GET", "POST"])
    def results():
        if request.method == "POST":
            usernames = request.form.get("usernames").split()
            useGenres = request.form.get("useGenres", type=bool)
            useTags = request.form.get("useTags", type=bool)
            useStaff = request.form.get("useStaff", type=bool)
            useStudios = request.form.get("useStudios", type=bool)
        return render_template('results.html')


    return app