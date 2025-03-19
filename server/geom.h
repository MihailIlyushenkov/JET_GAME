#ifndef _GEOM_H_
#define _GEOM_H_
#include <math.h>
/** Geometry library for rectangles */

typedef struct _point {
	double x;
	double y;
} Point;

typedef struct _dimension {
	double w;
	double h;
} Dimension;

typedef struct _rect {
	Dimension dim; /**< Rectange dimensions */
	Point center; /**< Rect center */
	double orient; /**< Orientation */
} Rect;

typedef struct _cone {
	Point center;
	double angle;
	double range;
} Cone;

/** Determines wheter two rects are in collision or not */
int rect_collision(Rect* r1, Rect* r2);

/** Point difference */

Point point_diff(Point a, Point b);
/** The length of vector */

int intercect(Rect* A, Rect* B);

int in_cone(Point A, Cone C, double global_cone_rotation);
double sub_angle(double a, double b);
double get_angle(Point a, Point b);
double ABS(double x);

#endif /* _GEOM_H_ */
