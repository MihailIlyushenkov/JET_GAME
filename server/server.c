#define _GNU_SOURCE
#include <stdio.h>
#include <uv.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <stdarg.h>
#include "geom.h"

#define MAX_NAME 32
/** Maximum number of weapon types */
#define MAX_WEAPONS 10
/** Maximum number  of players */
#define MAX_PLAYERS 10
/** Maximum number of currently launched missiles */
#define MAX_MISSILES 64

/** Key codes */
#define KEY_UP 1
#define KEY_DOWN 2
#define KEY_LEFT 3
#define KEY_RIGHT 4
#define KEY_LAUNCH 5

#define DT 0.02

#define MOD(x, y) sqrt((x) * (x) + (y) * (y))
#define SIGN(x) ((x) > 0) ? 1 : ((x < 0) ? (-1) : 0)

#define TICK 20 // tick time in milliseconds

/** Weapon configuration structure */
typedef struct _weapon
{
	char name[MAX_NAME];

	double w;
	double h;

	double turn_coeff;
	double maxlifetime;
	double enginedelay;
	double booster_time;
	double booster_force;
	double sustainer_time;
	double sustainer_force;
	double drag_coef;
	int type;
} Weapon;

typedef struct _radar
{
	double gim_limit;
	double angle[3];
	int range[3];
	double scanspeed;
	int mode; // 0 - off, 1 - search, 2 - tracking
	int dir;  // направление сканирования: 1 против часовой, -1 по часовой
	double fow;
	Cone cone;
	struct _player *found_new[MAX_PLAYERS];
	int found_new_count;
	struct _player *found_old[MAX_PLAYERS];
	int found_old_count;
	struct _player *tar_to_lock;
	struct _player *locked;
} Radar;

/** The player state and parameters */
typedef struct _player
{
	int status; /**< player status, 0 -- for disabled/killed, 1 - for enabled */
	char name[MAX_NAME];
	struct sockaddr_in addr;
	Rect rect;		/**< position and size */
	Point vel;		/** Velocity vector */
	double heading; /** azimuth */
	double speed;

	struct
	{
		int weaponid;
		int count;
	} weapons[MAX_WEAPONS];
	int nweapons; /**< number of weapons onboard */
	int chweapon; /*chosen weapon index*/
	double best_perf_speed;
	double thrust_coeff;
	double turn_coeff;

	Radar radar;

	int is_illuminated;
	int thrust;
	int thrust_acc;
	int turn_dir;
	int hittime;
} Player;

/** Launched missiles states */
typedef struct _missile
{
	int status;	  /**< current missile status */
	int weaponid; /**< type of weapon */
	int mtime;
	// int lifetime;
	int mesh_index;
	Rect rect;
	double heading; /**< azimuth */
	double speed;
	Player *PL_target;
	Player *PL_owner;
} Missile;

/** List of configured weapons */
int nweapons;
Weapon weapons[MAX_WEAPONS];

/** List of players */
int nplayers;
Player players[MAX_PLAYERS];

/** Launched missle slots */
int nmissles;
Missile missiles[MAX_MISSILES];

int32_t current_time = 0;

/** Global loop */
uv_loop_t *loop;
uv_udp_t server; /**< global server socket handler */

void alloc_buffer(uv_handle_t *client, size_t sz, uv_buf_t *buf)
{
	buf->base = malloc(sz);
	buf->len = sz;
}

void register_player(const uv_buf_t *buf, const struct sockaddr *addr);
void control(int i, int keycode, int turn, int launch, int ch_weapon, int ch_tar, int lock);

void process_control(const uv_buf_t *buf, const struct sockaddr *addr)
{
	int num, boost, turn, launch, ch_weapon, ch_tar, lock;
	// printf("get controls");
	if (sscanf(buf->base, "CTRL%d%d%d%d%d%d%d", &num, &boost, &turn, &launch, &ch_weapon, &ch_tar, &lock) == 7)
	{
		// printf("Control got from %d: %d %d %d %d %d %d\n", num, boost, turn, launch, ch_weapon, ch_tar, lock);
		for (int i = 0; i < nplayers; i++)
		{
			if (!players[i].status)
				continue;
			if (!memcmp(&players[i].addr, addr, sizeof(struct sockaddr_in)) && i == num)
			{
				control(i, boost, turn, launch, ch_weapon, ch_tar, lock);
				return;
			}
		}
	}
}

int launch_missile(Player *p)
{
	int j = -1;
	for (int i = 0; i < MAX_MISSILES; i++)
	{
		if (missiles[i].status == 0)
		{
			j = i;
			break;
		}
	}

	if (j == -1)
	{
		printf("too many missiles, cant launch");
		return 0;
	}

	if (p->weapons[p->chweapon].count >= 1)
	{
		Weapon temp = weapons[p->weapons[p->chweapon].weaponid];

		p->weapons[p->chweapon].count--;

		missiles[j].status = 1;
		missiles[j].heading = p->heading;
		missiles[j].speed = p->speed;

		missiles[j].mtime = 0;
		missiles[j].weaponid = p->weapons[p->chweapon].weaponid;

		missiles[j].rect.center.x = p->rect.center.x;
		missiles[j].rect.center.y = p->rect.center.y;
		missiles[j].rect.orient = p->heading;
		missiles[j].rect.dim.w = temp.w;
		missiles[j].rect.dim.h = temp.h;

		missiles[j].PL_target = p->radar.locked;
		missiles[j].PL_owner = p;
		nmissles++;
	}
	else
	{
		printf("out of missiles");
	}
	return 0;
}

void on_recv(uv_udp_t *handle, ssize_t nread, const uv_buf_t *buf,
			 const struct sockaddr *addr, unsigned flags)
{
	if (nread > 0)
	{
		printf("%ld bytes got from %p\n", nread, addr);
		if (nread > 7 && !strncmp(buf->base, "CONNECT", 7))
		{
			printf("Registering...\n");
			register_player(buf, addr);
		}
		else if (nread > 7 && !strncmp(buf->base, "CTRL", 4))
		{
			process_control(buf, addr);
		}
		else
		{
			printf("Unknown request\n");
		}
	}
}

void send_game_state_cb(uv_udp_send_t *req, int status)
{
	free(req);
}

void send_game_state(Player *p, char *buf, size_t sz)
{

	uv_buf_t wbuf = uv_buf_init(buf, sz);
	uv_udp_send_t *req = malloc(sizeof(uv_udp_send_t));
	uv_req_set_data((uv_req_t *)req, buf);
	uv_udp_send(req, &server, &wbuf, 1, (struct sockaddr *)&p->addr,
				send_game_state_cb);
}

#define nsdelta(ts1, ts2) (ts2.tv_sec - ts1.tv_sec) * 1000000000 + (ts2.tv_nsec - ts1.tv_nsec)

struct _objstate
{
	uint32_t num;		// 4
	int32_t status;		// 8
	int32_t x;			// 12
	int32_t y;			// 16
	float heading;		// 32
	uint32_t rdr_mode;	// 36
	float rdr_angle;	// 52
	uint32_t rdr_range; // 56
};

struct _state_hdr
{
	char pname[4];	 // 4
	int32_t objects; // 8
	int32_t curtime; // 12
};

struct _state
{
	struct _state_hdr hdr;
	struct _objstate objects[];
};

struct _state state;

void broadcast_game_state(long *dt1, long *dt2)
{
	size_t sz = 0;
	int i;
	Player *p;
	Player *pl;
	Missile *m;
	struct timespec t1, t2, t3;
	clock_gettime(CLOCK_MONOTONIC, &t1);
	/* Fill up state structure */
	state.hdr.objects = 0;
	// fprintf(stderr, "Broadcasting game state\n");
	memcpy(state.hdr.pname, "STAT", 4);
	state.hdr.curtime = current_time;
	// fprintf(stderr, "Writing players\n");
	for (p = players; p < players + nplayers; p++)
	{
		if (p->status)
			state.objects[state.hdr.objects++] =
				(struct _objstate){(p - players) | 0b10000000000000000, p->status,
								   p->rect.center.x, p->rect.center.y, p->heading,
								   p->radar.mode, p->radar.cone.angle, p->radar.cone.range};
	}
	// fprintf(stderr, "Writing missiles\n");
	for (m = missiles; m < missiles + MAX_MISSILES; m++)
	{
		if (m->status)
			state.objects[state.hdr.objects++] =
				(struct _objstate){m->weaponid | 0b01000000000000000, m->status,
								   m->rect.center.x, m->rect.center.y, m->heading,
								   0, 0, 0};
	}

	for (p = players; p < players + nplayers; p++)
	{
		if (p->status)
			for (int i = 0; i < p->radar.found_old_count; i++)
			{
				printf("sending radar (player #%ld) founded #%d/%d\n", p-players, i, p->radar.found_old_count);
				pl = p->radar.found_old[i];
				state.objects[state.hdr.objects++] =
					(struct _objstate){(p - players) | 0b00100000000000000, pl->status,
									   pl->rect.center.x, pl->rect.center.y, pl->heading,
									   (pl == p->radar.tar_to_lock) ? 1 : ((pl == p->radar.locked) ? 2 : 0), 0, 0};
			}
		if (p->radar.locked != 0)
		{
			pl = p->radar.locked;
			state.objects[state.hdr.objects++] =
				(struct _objstate){(p - players) | 0b00100000000000000, pl->status,
								   pl->rect.center.x, pl->rect.center.y, pl->heading, 2, 0, 0};
		}
	}

	/* Broadcasting */
	clock_gettime(CLOCK_MONOTONIC, &t2);
	// fprintf(stderr, "Sending %d objects...\n", state.hdr.objects);
	for (p = players; p < players + nplayers; p++)
	{
		if (!p->status)
			continue;
		// fprintf(stderr, "Sending to player %s\n", p->name);
		send_game_state(p, (char *)&state,
						sizeof(struct _state_hdr) + state.hdr.objects * sizeof(struct _objstate));
	}
	clock_gettime(CLOCK_MONOTONIC, &t3);
	*dt1 = nsdelta(t1, t2);
	*dt2 = nsdelta(t2, t3);
}

void game_step();

void on_timer(uv_timer_t *timer)
{
	struct timespec t1, t2, t3;
	long dt3, dt4;
	clock_gettime(CLOCK_MONOTONIC, &t1);
	game_step();
	// fprintf(stderr, "game_step called\n");
	clock_gettime(CLOCK_MONOTONIC, &t2);
	broadcast_game_state(&dt3, &dt4);
	clock_gettime(CLOCK_MONOTONIC, &t3);
	long dt = nsdelta(t1, t2);
	long dt2 = nsdelta(t2, t3);
	// fprintf(stderr, "%ld %ld\n", dt, dt2);
}

void on_send_cb(uv_udp_send_t *req, int status)
{
	free(req->data);
}

void send_to_addr(const struct sockaddr *addr, const char *format, ...)
{
	char *buf;
	va_list va;
	va_start(va, format);
	int sz = vasprintf(&buf, format, va);
	va_end(va);

	uv_buf_t wbuf = uv_buf_init(buf, sz);
	uv_udp_send_t *req = malloc(sizeof(uv_udp_send_t));
	uv_req_set_data((uv_req_t *)req, buf);
	uv_udp_send(req, &server, &wbuf, 1, addr,
				on_send_cb);
}

void register_player(const uv_buf_t *buf, const struct sockaddr *addr)
{
	int i;
	char name[MAX_NAME];
	if (sscanf(buf->base, "CONNECT %s", name) != 1)
	{
		send_to_addr(addr, "BAD COMMAND\n");
		return;
	}
	fprintf(stderr, "Trying to register %s\n", name);
	for (i = 0; i < nplayers; i++)
	{
		if (!players[i].status && !strcmp(name, players[i].name))
		{
			struct sockaddr_in *addr_in = (struct sockaddr_in *)addr;
			char *a = (char *)&(addr_in->sin_addr.s_addr);
			printf("Registering player from %hhu.%hhu.%hhu.%hhu:%d\n",
				   a[0], a[1], a[2], a[3], addr_in->sin_port);
			players[i].status = 1; /* make player active */
			players[i].addr = *addr_in;
			send_to_addr(addr, "PLAYAS %d\n", i);
			return;
		}
	}
	send_to_addr(addr, "NO VACANCY\n");
}

void check_player_collisions(Player *pl)
{
	for (Player *p = players; p < players + nplayers; p++)
	{
		if (p->status != 1)
			continue;
		if (p == pl)
			continue;
		// printf("checking %s: (%lf, %lf, %lf, %lf, %lf) and %s: (%lf, %lf, %lf, %lf, %lf)\n",
		// 	pl->name, pl->rect.center.x, pl->rect.center.y, pl->rect.dim.h, pl->rect.dim.w, pl->rect.orient,
		// 	p->name,p->rect.center.x, p->rect.center.y, p->rect.dim.h, p->rect.dim.w, p->rect.orient);

		if (intercect(&pl->rect, &p->rect))
		{
			/* two players collision */
			p->status = 2;
			pl->status = 2;
			printf("PLAYER COLL\n");
			return;
		}
	}
	for (Missile *m = missiles; m < missiles + MAX_MISSILES; m++)
	{
		if (m->status != 1)
			continue;
		// printf("pl is %p, m_owner is %p\n", pl, m->PL_owner);
		if (m->PL_owner == pl)
			continue;
		if (intercect(&pl->rect, &m->rect))
		{
			m->status = 2;
			pl->status = 2;
			printf("MISSLE HIT\n");
		}
	}
}

int in_arr(Player **arr, int arrlen, Player *tar)
{
	for (int i = 0; i < arrlen; i++)
	{
		if (arr[i] == tar)
			return 1;
	}
	return 0;
}

int clear_search_data(Radar *rdr)
{
	memset(rdr->found_new, 0, MAX_PLAYERS * sizeof(Player *));
	memset(rdr->found_old, 0, MAX_PLAYERS * sizeof(Player *));
	rdr->found_new_count = rdr->found_old_count = 0;
}

int radar_update(Player *pl)
{
	Radar *rdr = &pl->radar;

	rdr->cone.center = pl->rect.center;

	if (rdr->mode == 0)
		return 0;
	if (rdr->mode == 1)
	{
		double prob = rdr->cone.angle + rdr->scanspeed * rdr->dir;

		if (ABS(prob) < rdr->fow)
		{
			// printf("yay, moving array, old was %lf, new is %lf (dir: %d, speed: %lf, fow: %lf)\n",
			// rdr->cone.angle, prob, rdr->dir, rdr->scanspeed, rdr->fow);
			rdr->cone.angle = prob;
		}
		else
		{
			// printf("got to edge\n");
			rdr->dir *= -1;
			rdr->cone.angle += rdr->scanspeed * rdr->dir;

			if (rdr->tar_to_lock != 0)
			{
				if (!(in_arr(rdr->found_new, rdr->found_new_count, rdr->tar_to_lock)))
				{
					if (rdr->found_new_count == 0)
					{
						rdr->tar_to_lock = 0;
					}
					else
					{
						rdr->tar_to_lock = rdr->found_new[0];
					}
				}
			}

			for (int i = 0; i < MAX(rdr->found_new_count, rdr->found_old_count); i++)
			{
				rdr->found_old[i] = rdr->found_new[i];
				rdr->found_new[i] = 0;

				rdr->found_old_count = rdr->found_new_count;
				rdr->found_new_count = 0;
			}
		}
		int i = 0;
		for (Player *p = players; p < players + nplayers; p++, i++)
		{
			if (p == pl || p->status != 1)
				continue;
			if (in_cone(p->rect.center, pl->radar.cone, pl->heading) && !in_arr(rdr->found_new, rdr->found_new_count, p))
			{
				printf("FOUND DUDE %d, counts: new %d, old %d\n", i, rdr->found_new_count, rdr->found_old_count);
				rdr->found_new[rdr->found_new_count] = p;
				rdr->found_new_count += 1;
			}
		}

		if (pl->radar.found_old_count != 0) {
			printf("old_counst = %d\n", pl->radar.found_old_count);
		}
	}
	else if (rdr->mode == 2)
	{
		rdr->cone.angle = sub_angle(pl->heading, get_angle(pl->rect.center, rdr->locked->rect.center));
		if (ABS(rdr->cone.angle) > rdr->gim_limit)
		{
			rdr->tar_to_lock = 0;
			rdr->locked->is_illuminated = 0;
			rdr->locked = 0;
			rdr->mode = 1;
			rdr->cone.angle = 0;
			rdr->dir = 1;
		}
	}

	// if(pl == (Player*) (&players[0])){
	// 	Radar* rdr = &(pl->radar);
	// 	printf("mode: %d", rdr->mode);
	// 	printf("%lf/%lf\n", rdr->cone.angle, rdr->fow);
	// 	printf("oldcnt %d, newcnt %d\n", rdr->found_old_count, rdr->found_new_count);
	// 	printf("found_old:\n");
	// 	for(int i = 0; i < rdr->found_old_count; i++){
	// 		printf("\t%d/%d", i, rdr->found_old_count);
	// 		printf(" %s\n", rdr->found_old[i]->name);
	// 	}
	// 	printf("found_new:\n");
	// 	for(int i = 0; i < rdr->found_new_count; i++){
	// 		printf("\t%d/%d", i, rdr->found_new_count);
	// 		printf(" %s\n", rdr->found_new[i]->name);
	// 	}

	// 	if(rdr->locked == 0){
	// 		printf("locked: 0\n");
	// 	}
	// 	else{
	// 		printf("locked name:");
	// 		printf("%s ", rdr->locked->name);
	// 		printf("got it?\n");
	// 	}

	// 	if(rdr->tar_to_lock == 0){
	// 		printf("tar_to_lock: 0\n");
	// 	}
	// 	else{
	// 		printf("tar_to_lock: %s\n", rdr->tar_to_lock->name);
	// 	}
	// }
	return 0;
}

int radar_try_lock(Player *pl)
{
	Radar *rdr = &pl->radar;
	if (rdr->mode == 1)
	{
		if (rdr->tar_to_lock)
		{
			Cone FowCone = (Cone){rdr->cone.center, rdr->fow, rdr->cone.range};
			if (in_cone(rdr->tar_to_lock->rect.center, FowCone, pl->heading))
			{
				rdr->mode = 2;
				rdr->locked = rdr->tar_to_lock;
				rdr->locked->is_illuminated = 1;
				rdr->cone.angle = sub_angle(pl->heading, get_angle(pl->rect.center, rdr->locked->rect.center));
			}
		}
		else
		{
			rdr->cone.angle = 0;
		}
	}
	else if (rdr->mode == 2)
	{
		rdr->mode = 1;
		rdr->locked->is_illuminated = 0;
		rdr->locked = 0;
		rdr->mode = 1;
		rdr->cone.angle = 0;
		rdr->dir = 1;
	}

	clear_search_data(rdr);
}

int radar_switch_target(Player *pl)
{
	Radar *rdr = &pl->radar;
	if (rdr->tar_to_lock)
	{
		for (int i = 0; i < rdr->found_old_count; i++)
		{
			if ((Player *)&(rdr->found_old[i]) == rdr->tar_to_lock)
			{
				int next_index = (i + 1) % rdr->found_old_count;
				rdr->tar_to_lock = rdr->found_old[next_index];
			}
			return 0;
		}
	}
	else
	{
		rdr->tar_to_lock = rdr->found_old[0];
	}
	return 0;
}

void player_update(Player *pl)
{
	if (pl->status == 1)
	{
		if ((0 <= pl->thrust + pl->thrust_acc) && (pl->thrust + pl->thrust_acc <= 100))
		{
			pl->thrust += pl->thrust_acc;
		}
		// printf("thrust: %d, ass: %d\n", pl->thrust, pl->thrust_acc);

		pl->heading += (pl->turn_coeff * pl->turn_dir);
		if (pl->heading >= 2 * M_PI)
		{
			pl->heading -= 2 * M_PI;
		}
		if (pl->heading <= -2 * M_PI)
		{
			pl->heading += 2 * M_PI;
		}
		pl->speed = pl->thrust / 10.0;

		double sa, ca;
		sincos(pl->heading, &sa, &ca);

		pl->vel.x = pl->speed * ca; // same as 10*thrust/100 -> max speed (module)= 10, later may be add more complex formula
		pl->vel.y = pl->speed * sa;

		pl->rect.center.x += pl->vel.x;
		pl->rect.center.y += pl->vel.y;
		pl->rect.orient = pl->heading;

		radar_update(pl);
	}
	if (pl->status == 2)
	{
		pl->hittime++;
		if (pl->hittime >= 3 * 1000 / TICK)
		{
			pl->status = -1;
		}
	}
}

void navigate_to_point(Missile *m, Point p)
{
	double tar_angle = get_angle(m->rect.center, p);
	double diff = sub_angle(m->heading, tar_angle);

	double tcf = weapons[m->weaponid].turn_coeff;

	if (ABS(diff) <= tcf && ABS(diff) >= 0.01)
	{
		m->heading += diff;
	}
	else
	{
		m->heading += (diff > 0) ? (tcf) : (-tcf);
	}

	if (m->heading >= 2 * M_PI)
		m->heading -= 2 * M_PI;
	if (m->heading > 0)
		m->heading += 2 * M_PI;
}

int navigate_to_player(Missile *m)
{
	if (m->speed <= 0.3)
	{
		return 0;
	}

	Player *temp = m->PL_target;
	double time_to_hit = MOD(m->rect.center.x - temp->rect.center.x, m->rect.center.y - temp->rect.center.y) / m->speed;

	double sa, ca;
	sincos(temp->heading, &sa, &ca);

	Point intersection;
	intersection.x = temp->rect.center.x + temp->speed * ca * time_to_hit / 1.5;
	intersection.y = temp->rect.center.y + temp->speed * sa * time_to_hit / 1.5;

	navigate_to_point(m, intersection);
	return 0;
}

void missle_update(Missile *m)
{
	if (m->status == 1)
	{
		Weapon temp = weapons[m->weaponid];
		m->mtime++;

		if (m->mtime < temp.enginedelay)
		{
			// printf("delay\n");
		}

		if (temp.enginedelay < m->mtime && m->mtime < temp.booster_time)
		{
			m->speed += temp.booster_force - temp.drag_coef * (m->speed * m->speed);
			m->mesh_index = 1;
			// printf("booster\n");
		}
		else if (temp.booster_time < m->mtime && m->mtime < temp.sustainer_time)
		{
			m->speed += temp.sustainer_force - temp.drag_coef * (m->speed * m->speed);
			m->mesh_index = 2;
			// printf("sustainer\n");
		}
		else
		{
			m->speed -= temp.drag_coef * (m->speed * m->speed);
			m->mesh_index = 0;
			// printf("eng off\n");
		}

		if (m->PL_target != 0)
		{
			// printf("TAR NOT NULL");
			if (m->PL_target->status != 0)
			{
				//	printf("TARGET ACTIVe");
				if (temp.type == 2 || m->PL_target->is_illuminated == 1)
				{
					navigate_to_player(m);
					// printf("THE MISSLE KNOWS WHERE IT IS AT ALL TIMES\n");
				}
				else
				{
					// printf("LOST TRACK");
				}
			}
		}
		else
		{
			// printf("attempt to navigate to zero target");
		}

		double sa, ca;
		sincos(m->heading, &sa, &ca);

		// printf("mspeed: %lf", m->speed);
		m->rect.center.x += m->speed * ca;
		m->rect.center.y += m->speed * sa;
	}
	else if (m->status == 2)
	{
		memset(m, 0, sizeof(Missile));
	}
}

void control(int i, int boost, int turn, int launch, int ch_weapon, int ch_tar, int lock)
{
	Player *p = &players[i];

	p->thrust_acc = boost;
	p->turn_dir = turn;

	if (launch == 1)
	{ // adding new missle
		launch_missile(p);
	}

	if (ch_weapon == 1)
	{
		p->chweapon = (p->chweapon + 1) % (p->nweapons);
	}

	if (ch_tar == 1)
	{
		// for(int j = 0; j < nplayers; j++){
		// 	if(players[j].status == 1 && i != j){
		// 		p->radar.tar_to_lock = &players[j];
		// 	}
		// }
		radar_switch_target(p);
	}

	if (lock == 1)
	{
		// if(p->radar.tar_to_lock->status == 1 && p->radar.tar_to_lock != p) {
		// 	p->radar.locked = p->radar.tar_to_lock;
		// 	p->radar.locked->is_illuminated = 1;
		// }
		radar_try_lock(p);
	}
}

void game_step()
{
	Player *p;
	Missile *m;
	current_time++; /* increase the internal time counter */
	for (p = players; p < players + nplayers; p++)
	{
		int r, c;
		if (!p->status)
			continue;
		player_update(p);
	}

	for (m = missiles; m < missiles + nmissles; m++)
	{
		if (!m->status)
			continue;
		missle_update(m);
	}

	int i = 0;
	// printf("coll sect\n");
	for (p = players; p < players + nplayers; p++)
	{
		;
		if (p->status != 1)
			continue;
		// printf("cool for pl #%d/%d\n", i, nplayers);
		i += 1;
		check_player_collisions(p);
	}
	// printf("end coll sect\n");
}

typedef int (*settings_func)();

int player_name(char *buf, settings_func *next, int *arg);
int weapon_name(char *buf, settings_func *next, int *arg);

int player_settings(char *buf, settings_func *next, int *arg)
{
	if (sscanf(buf, "%lf%lf%lf",
			   &players[*arg].best_perf_speed,
			   &players[*arg].thrust_coeff,
			   &players[*arg].turn_coeff) == 3)
	{

		players[*arg].radar.range[0] = 1000; // желательно отдельное место для настроек радара
		players[*arg].radar.range[1] = 3000;
		players[*arg].radar.range[2] = 5000;
		players[*arg].radar.angle[0] = 15 * M_PI / 180;
		players[*arg].radar.angle[1] = 30 * M_PI / 180;
		players[*arg].radar.angle[2] = 60 * M_PI / 180;

		players[*arg].radar.gim_limit = 60 * M_PI / 180;
		players[*arg].radar.mode = 1;
		players[*arg].radar.dir = 1;

		players[*arg].radar.scanspeed = 1.5 * M_PI / 180;
		players[*arg].radar.cone.angle = 3 * M_PI / 180;
		players[*arg].radar.cone.range = players[*arg].radar.range[2];
		players[*arg].radar.fow = players[*arg].radar.angle[1];

		players[*arg].radar.tar_to_lock = 0;
		memset(players[*arg].radar.found_new, 0, sizeof(players[*arg].radar.found_new));
		memset(players[*arg].radar.found_old, 0, sizeof(players[*arg].radar.found_old));

		players[*arg].radar.found_new_count = 0;
		players[*arg].radar.found_old_count = 0;

		players[*arg].hittime = 0;

		if (*arg < nplayers - 1)
		{
			(*arg)++;
			*next = player_name;
		}
		else
		{
			*next = NULL;
		}
		return 0;
	}
	return -fprintf(stderr, "Player settings line expected but '%s' got\n", buf);
}

int player_weapons(char *buf, settings_func *next, int *arg)
{
	int w = 0;
	char *s = buf;
	char *t;
	fprintf(stderr, "Player weapons\n");
	while ((t = strsep(&s, ", \r\n")))
	{
		if (!strcmp(t, "None"))
			break;

		char *conf = t;
		char *name = strsep(&conf, ":\n");
		if (!name || !*name)
			break;
		int wpi;

		/* find weapon */
		fprintf(stderr, "Trying to find weapon '%s'\n", name);
		for (wpi = 0; wpi < nweapons; wpi++)
		{
			if (!strcmp(weapons[wpi].name, name))
			{
				/* found */
				players[*arg].weapons[w].weaponid = wpi;
				if (sscanf(conf, "%d", &players[*arg].weapons[w].count) != 1)
				{
					return -fprintf(stderr, "Weapons count expected for weapon %s player %d\n", name, *arg);
				}
				break;
			}
		}
		if (wpi == nweapons)
		{
			return -fprintf(stderr, "Weapon with name %s was not defined\n", name);
		}
		w++;
	}
	players[*arg].nweapons = w;
	*next = player_settings;
	return 0;
}

int player_pos(char *buf, settings_func *next, int *arg)
{
	if (sscanf(buf, "%lf%lf",
			   &players[*arg].rect.center.x,
			   &players[*arg].rect.center.y) == 2)
	{
		*next = player_weapons;
		return 0;
	}
	return -fprintf(stderr, "Player position expected, but %s got\n", buf);
}

int player_scale(char *buf, settings_func *next, int *arg)
{
	if (sscanf(buf, "%lf%lf",
			   &players[*arg].rect.dim.w,
			   &players[*arg].rect.dim.h) == 2)
	{
		*next = player_pos;
		return 0;
	}
	return -fprintf(stderr, "Player dimensions expected, but %s got\n", buf);
}

int player_files(char *buf, settings_func *next, int *arg)
{
	/* skip */
	*next = player_scale;
	return 0;
}

int player_name(char *buf, settings_func *next, int *arg)
{
	if (sscanf(buf, "%s", players[*arg].name) == 1)
	{
		fprintf(stderr, "Player %s added\n", players[*arg].name);
		*next = player_files;
		return 0;
	}
	return -fprintf(stderr, "Player name expected, but '%s' got\n", buf);
}

int players_num(char *buf, settings_func *next, int *arg)
{
	if (sscanf(buf, "%d", &nplayers) == 1)
	{
		*arg = 0;
		*next = player_name;
		return 0;
	}
	return -fprintf(stderr, "Players number expected, but '%s' got\n", buf);
}

int players_section(char *buf, settings_func *next, int *arg)
{
	if (!strncmp(buf, "$players$", 9))
	{
		*next = players_num;
		return 0;
	}
	return -fprintf(stderr, "Players section expected, but '%s' got\n", buf);
}

int weapon_settings(char *buf, settings_func *next, int *arg)
{
	if (sscanf(buf, "%lf%lf%lf%lf%lf%lf%lf%lf%d",
			   &weapons[*arg].turn_coeff,
			   &weapons[*arg].maxlifetime,
			   &weapons[*arg].enginedelay,
			   &weapons[*arg].booster_time,
			   &weapons[*arg].booster_force,
			   &weapons[*arg].sustainer_time,
			   &weapons[*arg].sustainer_force,
			   &weapons[*arg].drag_coef,
			   &weapons[*arg].type) == 9)
	{

		weapons[*arg].maxlifetime *= 1000 / TICK;
		weapons[*arg].enginedelay *= 1000 / TICK;
		weapons[*arg].booster_time *= 1000 / TICK;
		weapons[*arg].sustainer_time *= 1000 / TICK;

		weapons[*arg].booster_time += weapons[*arg].enginedelay;
		weapons[*arg].sustainer_time += weapons[*arg].booster_time;

		if (*arg < nweapons - 1)
		{
			*next = weapon_name;
			(*arg)++;
		}
		else
		{
			*next = players_section;
		}
		return 0;
	}
}

int weapon_files(char *buf, settings_func *next, int *arg)
{
	/* skip it, make sense only for client */
	*next = weapon_settings;
	return 0;
}

int weapon_scale(char *buf, settings_func *next, int *arg)
{
	if (sscanf(buf, "%lf %lf", &weapons[*arg].w, &weapons[*arg].h) == 2)
	{
		*next = weapon_files;
		return 0;
	}
	return -fprintf(stderr, "Weapon %d: dimentions expected, but '%s' got\n", *arg, buf);
}

int weapon_name(char *buf, settings_func *next, int *arg)
{
	if (sscanf(buf, "%s", weapons[*arg].name) == 1)
	{
		*next = weapon_scale;
		return 0;
	}
	return -fprintf(stderr, "Weapon %d: name expected, but '%s' got\n", *arg, buf);
}

int weapons_num(char *buf, settings_func *next, int *arg)
{
	if (sscanf(buf, "%d", &nweapons) == 1)
	{
		*arg = 0;
		*next = weapon_name;
		return 0;
	}
	return -fprintf(stderr, "Number of weapons expected, but '%s' got\n", buf);
}

int weapons_section(char *buf, settings_func *next, int *arg)
{
	if (!strncmp("$weapons$", buf, 9))
	{
		*next = weapons_num;
		return 0;
	}
	return -fprintf(stderr, "Weapons section expected, but '%s' got\n", buf);
}

int read_settings(FILE *f)
{
	char buf[1024];
	int mode = 0; /* 0 -- default, positive - weapon */
	settings_func func = weapons_section;
	int arg;
	while (func && fgets(buf, sizeof(buf), f) != NULL)
	{
		char *s = buf;
		while (*s == ' ' || *s == '\t')
			s++;
		if (*s == '#') /* this is a comment */
			continue;
		if (*s == '\n') /* empty line */
			continue;
		if (func(buf, &func, &arg))
		{
			return -fprintf(stderr, "Parsing of settings failed\n");
		}
	}
	return 0;
}

int DUMP(void)
{
	printf("DATA:\n");
	printf("nplayers: %d\n", nplayers);
	Player pl_temp;
	for (int i = 0; i < nplayers; i++)
	{
		pl_temp = players[i];
		printf("%s has %d weapons:\n", pl_temp.name, pl_temp.nweapons);
		for (int j = 0; j < pl_temp.nweapons; j++)
		{
			printf("\tweapon %d: %d %d\n", j, pl_temp.weapons[j].weaponid, pl_temp.weapons[j].count);
		}
		printf("rect parms: x: %lf, y: %lf, dim:%lf, %lf, orient: %lf\n",
			   pl_temp.rect.center.x, pl_temp.rect.center.y, pl_temp.rect.dim.w, pl_temp.rect.dim.h, pl_temp.rect.orient);
	}

	printf("WEAPONS\n");
	printf("nweapons: %d\n", nweapons);
	Weapon wp_temp;
	for (int i = 0; i < nweapons; i++)
	{
		wp_temp = weapons[i];
		printf("weapon #%d is %s, bsf: %lf, bst: %lf, drgcoeff: %lf, enginedel: %lf, maxlifetime: %lf, sustf: %lf, susttime: %lf, turncoeff: %lf, type: %d\n",
			   i, wp_temp.name,
			   wp_temp.booster_force, wp_temp.booster_time, wp_temp.drag_coef,
			   wp_temp.enginedelay, wp_temp.maxlifetime, wp_temp.sustainer_force,
			   wp_temp.sustainer_time, wp_temp.turn_coeff, wp_temp.type);
	}
	return 0;
}

int main()
{
	uv_timer_t timer;
	struct sockaddr_in addr;
	FILE *settings;
	loop = uv_default_loop();

	memset(players, 0, sizeof(players));
	memset(weapons, 0, sizeof(weapons));
	memset(missiles, 0, sizeof(missiles));
	printf("Reading settings file...\n");
	if (settings = fopen("../data/settings.txt", "r"))
	{
		if (read_settings(settings))
		{
			printf("Error while reading settings\n");
			fclose(settings);
			return -1;
		}
		fclose(settings);
	}
	else
	{
		printf("Error while opening settings file\n");
		return -1;
	}

	DUMP();

	uv_udp_init(loop, &server);
	// uv_ip4_addr("192.168.50.164", 9921, &addr);
	// uv_ip4_addr("10.55.128.182", 9921, &addr);
	uv_ip4_addr("0.0.0.0", 9921, &addr);
	uv_udp_bind(&server, (const struct sockaddr *)&addr, 0);
	printf("Starting server\n");
	uv_udp_recv_start(&server, alloc_buffer, on_recv);

	uv_timer_init(loop, &timer);
	printf("Starting timer\n");
	uv_timer_start(&timer, on_timer, 100, TICK);

	int result = uv_run(loop, UV_RUN_DEFAULT);
	return result;
}
