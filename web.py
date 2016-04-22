from flask import Flask, render_template, request, redirect, url_for, g, flash
from database import DBHandler
import re

app = Flask(__name__)
app.config.from_pyfile('flask.conf')
regexpip = "^(((25[1-5])|(2[1-4][0-9])|([0-1]?[0-9]{1,2}))\.){3,3}\
((25[1-5])|(2[1-4][0-9])|([0-1]?[0-9]{1,2}))$"



@app.before_request
def prepare():
    g.database = DBHandler("settings.conf")


@app.teardown_request
def clean(exc):
    db = getattr(g, 'database', None)
    if db is not None:
        db.__del__()


@app.route('/')
def main():
    rt = ({'name': row[0], 'ext_ip': row[1]} for row in g.database.get_routers())
    sw = ({'ext_p': rows[0], 'ip': rows[1], 'int_p': rows[2]}
          for rows in g.database.get_switchings())
    return render_template('main.html', routers=rt, switching=sw)


@app.route('/get/routers/edit/<string:name>', methods=['GET'])
def redirect_edit_router(name):
    res = g.database.get_router(name)
    return render_template('edit_router.html', name=res[0], ip=res[1])


@app.route('/get/switching/edit/<int:port>', methods=['GET'])
def redirect_edit_switching(port):
    res = g.database.get_switching(port)
    return render_template('edit_switching.html', ext_p=res[0], ip=res[1], int_p=res[2])


@app.route('/post/routers/edit/<string:name>', methods=['POST'])
def edit_router(name):
    new_name = request.form.get('name', None)
    ip = request.form.get('ip', None)
    if name is None or ip is None:
        flash('Smth bad has happened')
        return redirect(url_for('redirect_edit_router', name=name))
    elif len(new_name) == 0:
        flash("Empty name")
        return redirect(url_for('redirect_edit_router', name=name))
    elif re.match(regexpip, ip) is None:
        flash("Bad IP address")
        return redirect(url_for('redirect_edit_router', name=name))
    else:
        flash(g.database.edit_router(name, ip, new_name))
        return redirect(url_for('main'))


@app.route('/post/switching/edit/<int:port>', methods=['POST'])
def edit_switching(port):
    new_ep = request.form.get('ext_p', None)
    ip = request.form.get('ip', None)
    new_p = request.form.get('int_p', None)
    if new_ep is None or ip is None or new_p is None:
        flash('Smth bad has happened')
        return redirect(url_for('redirect_edit_switching', port=port))
    elif new_ep.isdigit() is False:
        flash("Bad external port")
        return redirect(url_for('redirect_edit_switching', port=port))
    elif new_p.isdigit() is False:
        flash("Bad internal port")
        return redirect(url_for('redirect_edit_switching', port=port))
    elif re.match(regexpip, ip) is None:
        flash("Bad IP address")
        return redirect(url_for('redirect_edit_switching', port=port))
    else:
        flash(g.database.edit_switching(port, new_ep, ip, new_p))
        return redirect(url_for('main'))


@app.route('/post/routers/add', methods=['POST'])
def add_router():
    name = request.form.get('name', None)
    ip = request.form.get('ip', None)
    if name is None or ip is None:
        flash('Smth bad has happened')
    elif len(name) == 0:
        flash('No name supplied')
    elif re.match(regexpip, ip) is None:
        flash("Bad IP address")
    else:
        flash(g.database.add_router(name, ip))
    return redirect(url_for('main'))


@app.route('/post/switching/add', methods=['POST'])
def add_switching():
    ext_p = request.form.get('ext_p', None)
    ip = request.form.get('ip', None)
    int_p = request.form.get('int_p', None)
    if ext_p is None or ip is None or int_p is None:
        flash('Smth bad has happened')
    elif ext_p.isdigit() is False:
        flash("Bad external port")
    elif int_p.isdigit() is False:
        flash("Bad internal port")
    elif re.match(regexpip, ip) is None:
        flash("Bad IP address")
    else:
        flash(g.database.add_switching(ext_p, ip, int_p))
    return redirect(url_for('main'))

app.run()


