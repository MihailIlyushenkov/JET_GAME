LDFLAGS+=$(shell pkg-config --libs libuv)
CFLAGS+=$(pkg-config --cflags libuv)

LDFLAGS+=-lm

CFLAGS+=-g

jetserver: server.o geom.o
	$(CC) -o $@ $^ $(LDFLAGS)

%.o: %.c
	$(CC) $(CFLAGS) -c -o $@ $<

