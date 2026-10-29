// SPDX-License-Identifier: GPL-2.0
/*
 * ti_walk.c - task information report (Member 2)
 *
 * This first implementation reports the selected task and its parent.
 * Ancestor and child traversal is added in a follow-up change.
 */
#include <linux/kernel.h>
#include <linux/sched.h>
#include <linux/pid.h>
#include <linux/rcupdate.h>
#include <linux/version.h>
#include "ti_walk.h"

static unsigned int ti_state(struct task_struct *task)
{
#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 14, 0)
	return READ_ONCE(task->__state);
#else
	return READ_ONCE(task->state);
#endif
}

static const char *ti_state_name(struct task_struct *task)
{
	unsigned int state = ti_state(task);

	if (task->exit_state & EXIT_ZOMBIE)
		return "EXIT_ZOMBIE";
	if (task->exit_state & EXIT_DEAD)
		return "EXIT_DEAD";
	if (state == TASK_RUNNING)
		return "TASK_RUNNING";
	if (state & TASK_INTERRUPTIBLE)
		return "TASK_INTERRUPTIBLE";
	if (state & TASK_UNINTERRUPTIBLE)
		return "TASK_UNINTERRUPTIBLE";
	if (state & __TASK_STOPPED)
		return "__TASK_STOPPED";
	if (state & __TASK_TRACED)
		return "__TASK_TRACED";
	return "OTHER";
}

#define EMIT(...) \
	do { \
		if (len < (int)size) \
			len += scnprintf(buf + len, size - len, __VA_ARGS__); \
	} while (0)

int ti_build_report(pid_t pid, char *buf, size_t size)
{
	struct task_struct *task, *parent;
	char command[TASK_COMM_LEN], parent_command[TASK_COMM_LEN];
	int len = 0;

	rcu_read_lock();

	task = pid_task(find_vpid(pid), PIDTYPE_PID);
	if (!task) {
		rcu_read_unlock();
		return 0;
	}

	get_task_comm(command, task);
	EMIT("command = [%s] pid = [%d] state = [%u]\n",
	     command, task_pid_vnr(task), ti_state(task));
	EMIT("state_name = [%s]\n", ti_state_name(task));

	parent = rcu_dereference(task->real_parent);
	if (parent && parent != task && task_tgid_vnr(parent) != 0) {
		get_task_comm(parent_command, parent);
		EMIT("ppid = [%d] parent_command = [%s]\n",
		     task_tgid_vnr(parent), parent_command);
	} else {
		EMIT("ppid = [0] parent_command = [-]\n");
	}

	rcu_read_unlock();
	return len;
}
