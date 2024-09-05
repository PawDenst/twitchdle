# main.py
from flask import Flask, render_template, Blueprint


main_app = Blueprint('main_app', __name__)


@main_app.route('/')
def main():
    return render_template('main.html')
