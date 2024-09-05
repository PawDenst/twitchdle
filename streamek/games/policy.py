# main.py
from flask import Flask, render_template, Blueprint


policy_app = Blueprint('policy_app', __name__)


@policy_app.route('/privacy_policy')
def main():
    return render_template('policy.html')
