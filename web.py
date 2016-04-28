from flask import Flask, render_template, request, redirect, url_for, g, flash
from database import DBHandler
import re, paramiko
from configparser import ConfigParser

# DEB: /etc/default/iptables
# RPM: /etc/sysconfig/iptables

app = Flask(__name__)
app.config.from_pyfile('flask.conf')
regexpip = "^(((25[1-5])|(2[1-4][0-9])|([0-1]?[0-9]{1,2}))\.){3,3}\
((25[1-5])|(2[1-4][0-9])|([0-1]?[0-9]{1,2}))$"
parser = ConfigParser()
parser.read(filenames='settings.conf')
ssh_port = parser.getint(section="SSH", option="port")
path = parser.get(section="SSH", option="path")
intf = parser.get(section="SSH", option="oif")

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


@app.route('/get/routers/add', methods=['GET'])
def add_router_red():
    return render_template('add_router.html')


@app.route('/get/switching/add', methods=['GET'])
def add_switching_red():
    return render_template('add_switching.html')


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


@app.route('/get/ssh/send/<string:router>', methods=["GET"])
def ssh_send(router):
    return render_template('ssh_info.html', hostname=router)


@app.route('/post/ssh/put/<string:router>', methods=["POST"])
def ssh_put(router):
    login = request.form.get('login', None)
    pw = request.form.get('pass', None)
    if login is None or pw is None:
        flash('Smth bad has happened')
    else:
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            rt, ip = g.database.get_router(router)
            client.connect(hostname=ip, username=login, password=pw, port=ssh_port)
            stdin, stdout, stderr = client.exec_command("")
            fclient = client.open_sftp()
            file = fclient.open(path, "w")
            sw = g.database.get_switchings()
            res = []
            file.write('*nat\n')
            file.write(":PREROUTING ACCEPT [0:0]\n")
            file.write(":INPUT ACCEPT [0:0]\n")
            file.write(":OUTPUT ACCEPT [0:0]\n")
            file.write(":POSTROUTING ACCEPT [0:0]\n")

            for line in sw:
                file.write("-A PREROUTING -d {eip}/32 -p tcp -m tcp --dport {ep}"
                            " -j DNAT --to-destination {ip}:{p}\n".format(eip=ip, ep=line[0],
                                                                        ip=line[1], p=line[2]))
            file.write("-A POSTROUTING -p tcp -m tcp -o {int} -j MASQUERADE\n".format(int=intf))
            file.write("COMMIT\n")
            file.flush()
            file.close()
            fclient.close()
            client.exec_command('iptables-restore < {path}'.format(path=path))

            flash("Successful sending")
        except OSError as err:
            flash(err.__str__())
        except paramiko.AuthenticationException as err:
            flash(err.__str__())
    return redirect(url_for('main'))


@app.route('/get/router/delete/<string:router>', methods=['GET'])
def delete_router(router):
    flash(g.database.delete_router(router))
    return redirect(url_for('main'))


@app.route('/get/switching/delete/<string:port>', methods=['GET'])
def delete_switching(port):
    flash(g.database.delete_switching(port))
    return redirect(url_for('main'))


app.run(host='0.0.0.0')
