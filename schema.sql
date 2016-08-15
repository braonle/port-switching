CREATE TABLE routers (
id INTEGER PRIMARY KEY,
extern_ip TEXT NOT NULL UNIQUE,
name TEXT NOT NULL UNIQUE
);
CREATE TABLE forwarding (
id INTEGER PRIMARY KEY,
extern_port INTEGER NOT NULL UNIQUE,
intern_ip TEXT NOT NULL,
intern_port INTEGER NOT NULL,
UNIQUE(intern_ip, intern_port)
);