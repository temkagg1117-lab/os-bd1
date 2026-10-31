/* SPDX-License-Identifier: GPL-2.0 */
/*
 * ti_walk.h - task hierarchy walker (Member 2)
 *
 * Builds the text report that is returned by a read of /proc/pid.
 */
#ifndef TI_WALK_H
#define TI_WALK_H

#include <linux/types.h>

#define TI_MAX_ANCESTORS 64   /* safety bound on the walk towards init   */
#define TI_MAX_CHILDREN  128  /* safety bound on child lines per report  */

/*
 * Fill @buf (size @size) with the report for process @pid.
 * Returns the number of bytes written, or 0 when @pid does not name a
 * live task (textbook: "the read function should return 0").
 * Never sleeps while holding RCU; @buf must be allocated by the caller.
 */
int ti_build_report(pid_t pid, char *buf, size_t size);

#endif /* TI_WALK_H */
