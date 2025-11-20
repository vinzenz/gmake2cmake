all: app

app: libcore.a
	cc -c app/main.c -o app

libcore.a: core.c
	cc -c core.c -o libcore.a
