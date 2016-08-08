import sqlite3
from configparser import ConfigParser


class DBHandler:
    def __init__(self, conf):
        self.parser = ConfigParser()
        self.parser.read(filenames=conf)
        # Contains strings for executing SQL-specific queries
        self.strings = {}
        self.conn = None
        # Getting handlers for different SQL agents
        conns = self.__handlers_init()
        # Realizing which SQL to deal with
        conn_init = conns.get(self.parser.get(section="DATABASE", option="type"))
        if conn_init is None:
            raise AttributeError("Not supported DB type")
        conn_init()

    def __handlers_init(self):
        conns = {'sqlite3': self.__sqlite3_init}
        return conns

    def __sqlite3_init(self):
        self.conn = sqlite3.connect(database=self.parser.get(section="DATABASE", option="database"))
        self.strings['add_router'] = "INSERT INTO routers VALUES(?,?)"
        self.strings['add_forwarding'] = "INSERT INTO switching VALUES(?,?,?)"
        self.strings['select_routers'] = "SELECT name, extern_ip from routers ORDER BY name"
        self.strings['select_router'] = "SELECT name, extern_ip from routers WHERE name = ?"
        self.strings['select_forwardings'] = "SELECT extern_port, intern_ip, intern_port " \
                                            "from switching ORDER BY extern_port"
        self.strings['select_forwarding'] = "SELECT extern_port, intern_ip, intern_port " \
                                           "from switching WHERE extern_port = ?"
        self.strings['edit_router'] = "UPDATE routers SET name = ?, extern_ip = ? WHERE name = ?"
        self.strings['edit_forwarding'] = "UPDATE switching SET extern_port = ?, intern_ip = ?," \
                                         "intern_port = ? WHERE extern_port = ?"
        self.strings['delete_router'] = "DELETE from routers WHERE name = ?"
        self.strings['delete_forwarding'] = "DELETE from switching WHERE extern_port = ?"

    def add_router(self, name, ext_ip):
        try:
            self.conn.cursor().execute(self.strings['add_router'], (ext_ip, name))
            self.conn.commit()
            res = (False, "{name} : {addr} added".format(name=name, addr=ext_ip))
        except sqlite3.IntegrityError as err:
            res = (True, str(err))
        return res

    def add_forwarding(self, ext_port, int_ip, int_port):
        try:
            self.conn.cursor().execute(self.strings['add_forwarding'], (ext_port, int_ip, int_port))
            self.conn.commit()
            res = (False, "forwarding rule {ext_port} -> {ip}:{int_port} added".format(
                ext_port=ext_port, ip=int_ip, int_port=int_port))
        except sqlite3.IntegrityError as err:
            res = (True, str(err))
        return res

    def get_routers(self):
        res = []
        cur = self.conn.cursor()
        cur.execute(self.strings['select_routers'])
        return cur.fetchall()

    def get_forwardings(self):
        res = []
        cur = self.conn.cursor()
        cur.execute(self.strings['select_forwardings'])
        return cur.fetchall()

    def get_router(self, router):
        cur = self.conn.cursor()
        cur.execute(self.strings['select_router'], (router,))
        return cur.fetchone()

    def get_forwarding(self, port):
        cur = self.conn.cursor()
        cur.execute(self.strings['select_forwarding'], (port,))
        return cur.fetchone()

    def edit_router(self, router, ip, name):
        """Returns a tuple with the first argument to indicate
        whether an error occurred (set True in this case)
        and the second one with the actual result"""
        cur = self.conn.cursor()
        try:
            cur.execute(self.strings['edit_router'], (name, ip, router))
            self.conn.commit()
            res = (False, "{router} -> {name} : {ip} changed".format(router=router, name=name, ip=ip))
        except sqlite3.IntegrityError as err:
            res = (True, str(err))
        return res

    def edit_forwarding(self, port, new_ep, ip, new_p):
        """Returns a tuple with the first argument to indicate
        whether an error occurred (set True in this case)
        and the second one with the actual result"""
        cur = self.conn.cursor()
        try:
            cur.execute(self.strings['edit_forwarding'], (new_ep, ip, new_p, port))
            self.conn.commit()
            res = (False, "{port} -> {new_ep} into {ip}:{new_p}".format(
                port=port, new_ep=new_ep, ip=ip, new_p=new_p))
        except sqlite3.IntegrityError as err:
            res = (True, str(err))
        return res

    def delete_router(self, name):
        cur = self.conn.cursor()
        try:
            cur.execute(self.strings['delete_router'], (name,))
            self.conn.commit()
            res = "Router {name} deleted".format(name=name)
        except sqlite3.IntegrityError as err:
            res = str(err)
        return res

    def delete_forwarding(self, port):
        cur = self.conn.cursor()
        try:
            cur.execute(self.strings['delete_forwarding'], (port,))
            self.conn.commit()
            res = "forwarding rule for {port} deleted".format(port=port)
        except sqlite3.IntegrityError as err:
            res = str(err)
        return res

    def __del__(self):
        self.conn.close()
