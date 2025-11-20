include config.mk

all: libcore.a app

libcore.a: src/core.c
	cc -Icoreinc -DCORE_DEF -c src/core.c -o libcore.a

app: src/main.c
	cc -Iappinc -DAPP_DEF -c src/main.c -o app
