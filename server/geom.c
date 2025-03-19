#define _GNU_SOURCE
#include <math.h>
#include "geom.h"


#define MAX(a, b) ((a)>(b)?(a):(b))
#define METRIC(p) ((p).x*(p).x+(p).y * (p).y)

double ABS(double x){
	if(x > 0.000001) return x;
	if(-0.000001 <= x && x <= 0.000001) return 0;
	else return -x;
}

Point point_diff(Point a, Point b) {
	return (Point){a.x-b.x, a.y - b.y}; //возвращает координаты вектора a-b
}

Point edge_norm(Point a, Point b) {
	return (Point){b.y - a.y, a.x - b.x}; //возвращает вектор (a-b) транспонированный
}


void rotate(Point* p, int npoints, double c, double s) { //поворачивает точки прямоугольника на sin = x, cos = c
	for(int i = 0; i < npoints; i++ ) 
		p[i] = (Point){p[i].x*c - p[i].y*s, p[i].x*s + p[i].y*c};
}

void translate(Point* p, int npoints, Point t) { // сдвинуть каждую точку массива p на ветктор t
	for(int i = 0; i < npoints; i++ ) 
		p[i] = (Point){p[i].x + t.x, p[i].y + t.y};
}

double dot(Point a, Point b) { //скалярное произведение векторов a и b
	return a.x*b.x + a.y*b.y;
}

int rect_points(Rect* r, Point* p) {
	double sx, cx;
	Dimension d = r->dim;
	sincos(r->orient, &sx, &cx);

	p[0] = (Point){d.w/2, d.h/2};
	p[1] = (Point){d.w/2, -d.h/2};
	p[2] = (Point){-d.w/2, -d.h/2};
	p[3] = (Point){-d.w/2, d.h/2};
	rotate(p, 4, cx, sx);
	translate(p, 4, r->center);
	return 0;
}

int _find_split(Point* v, Point*  a, Point* b) {
	for ( int i = 0; i < 4; i++ ) {
		Point norm = edge_norm(v[i], v[(i+1)%4]);
		double mina, minb, maxa, maxb;
		for( int j = 0; j < 4; j++ ) {
			double na = dot(a[j], norm);
			double nb = dot(b[j], norm);
			maxa = (!j || na > maxa)?na:maxa;
			maxb = (!j || nb > maxb)?nb:maxb;
			mina = (!j || na < mina)?na:mina;
			minb = (!j || nb < minb)?nb:minb;
		}
		/* check if the i'th edge splits points */
		if ( mina > maxb || minb > maxa) return 1;
	}
	/* splitting edge not found */
	return 0;
}


int rect_collision(Rect* r1, Rect* r2) {
	/* try to find an edge which splits vertices of both rects */
	Point a[4];
	Point b[4];
	/* getting rect points */
	rect_points(r1, a);
	rect_points(r2, b);
	/* iterating over edges */
	if ( _find_split(a, a, b) || _find_split(b, a, b) ) return 0;
	return 1;
}


int inbounds(Rect* A, Point B){ //для прямоугольника, параллельного осям координат c центром в (0,0)
    return ((-A->dim.w/2 <= B.x && B.x <= A->dim.w/2) && 
        (- A->dim.h/2 <= B.y && B.y <= A->dim.h/2))?1:0;
}

Point rotate_point(Point* A, double angle){
    Point B;
    B.x = A->x*cos(angle) - A->y*sin(angle);
    B.y = A->x*sin(angle) + A->y*cos(angle);
    return B;
}
#define MIN(x, y) ((x) < (y))?(x):(y)
// рабочая функции перечечения 
int intercect(Rect* A, Rect* B){
    Point temp1, temp2;
    Point Apoints[4];
    Point Bpoints[4];
    temp1.x = 0;
    temp1.y = 0;
    temp2.x = 0;
    temp2.y = 0;

    rect_points(A, Apoints);
    rect_points(B, Bpoints);

	temp1 = point_diff(A->center, B->center);
	double minA = MIN(A->dim.h, A->dim.w);
	double minB = MIN(B->dim.h, B->dim.w);
	if (METRIC(temp1) <= minA*minA || METRIC(temp1) <= minB*minB){
		return 1;
	}

    for(int i = 0; i < 4; i++){
        temp1 = point_diff(Bpoints[i], A->center);
        temp2 = rotate_point(&temp1, -A->orient);
        if (inbounds(A, temp2)){
            return 1;
        }
    }
    for(int i = 0; i < 4; i++){
        temp1 = point_diff(Apoints[i], B->center);
        temp2 = rotate_point(&temp1, -B->orient);
        if (inbounds(B, temp2)){
            return 1;
        }
    }
    return 0;
}

////// углы
double get_angle(Point a, Point b){ //угол на точку b из точки a (отсчет от оси x, в радианах от 0 до 2pi) 
	double x = b.x - a.x;
	double y = b.y - a.y;
	double angle = atan2(y, x);
	return (angle > 0)?(angle):(2*M_PI + angle);
}

double sub_angle(double a, double b){
	if (b == a){
		return 0;
	}
	else if (b > a){
		if (b - a <= M_PI) return b-a;
		else return -a - (2*M_PI - b);
	}
	else{
		if (a - b <= M_PI) return -(a-b);
		else return (b + (2*M_PI - a));
	}
}

double get_range(Point A, Point B){
	return sqrt((A.x - B.x)*(A.x - B.x) + (A.y- B.y)*(A.y - B.y));
}
//////конусы


int in_cone(Point A, Cone C, double global_cone_rotation){
	if (get_range(C.center, A) > C.range) return 0;
	if (ABS(sub_angle(global_cone_rotation, get_angle(C.center, A))) <= (C.angle)){
		return 1;
	}
	return 0;
}

