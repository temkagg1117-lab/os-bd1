// SPDX-License-Identifier: GPL-2.0
/*

 * ti_walk.c - task hierarchy walker (Member 2)
 *
 * Output format (one record per line, every value in [brackets]):
 *
 *   command = [bash] pid = [1395] state = [1]        <- textbook format
 *   state_name = [TASK_INTERRUPTIBLE]
 *   ppid = [1200] parent_command = [sshd]
 *   nchildren = [2]
 *   ancestor: pid = [1] command = [systemd] state = [1]   (root first)
 *   child: pid = [1400] command = [ls] state = [0]
 *   truncated = [children]                            (only when capped)
 *
 * Locking: everything is done under rcu_read_lock(). Children are found
 * with for_each_process() + real_parent so that no tasklist_lock (not
 * exported to modules) is needed.
 * ti_walk.c - task information report (Member 2)
 *
 * Reports the selected task, its parent, ancestors, and child processes.
 */
#include <linux/kernel.h>
#include <linux/sched.h>
#include <linux/sched/signal.h>
#include <linux/pid.h>
#include <linux/rcupdate.h>
#include <linux/version.h>
#include "ti_walk.h"

<<<<<<< HEAD
static unsigned int ti_state(struct task_struct *t)
{
#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 14, 0)
	return READ_ONCE(t->__state);
#else
	return READ_ONCE(t->state);
#endif
}

static const char *ti_state_name(struct task_struct *t)
{
	unsigned int s = ti_state(t);

	if (t->exit_state & EXIT_ZOMBIE)
		return "EXIT_ZOMBIE";
	if (t->exit_state & EXIT_DEAD)
		return "EXIT_DEAD";
	if (s == TASK_RUNNING)
		return "TASK_RUNNING";
	if (s & TASK_INTERRUPTIBLE)
		return "TASK_INTERRUPTIBLE";
	if (s & TASK_UNINTERRUPTIBLE)
		return "TASK_UNINTERRUPTIBLE";
	if (s & __TASK_STOPPED)
		return "__TASK_STOPPED";
	if (s & __TASK_TRACED)
=======
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
>>>>>>> 23f771c28187b4ac3c9f46b2cbf021da7abe366d
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
<<<<<<< HEAD
	struct task_struct *task, *par, *p;
	char comm[TASK_COMM_LEN], pcomm[TASK_COMM_LEN];
	struct task_struct *anc[TI_MAX_ANCESTORS];
	int nanc = 0, nchild = 0, shown = 0, i, len = 0;
=======
	struct task_struct *task, *parent, *process;
	struct task_struct *ancestors[TI_MAX_ANCESTORS];
	char command[TASK_COMM_LEN], parent_command[TASK_COMM_LEN];
	int ancestor_count = 0, child_count = 0, shown_children = 0;
	int i, len = 0;
>>>>>>> 23f771c28187b4ac3c9f46b2cbf021da7abe366d

	rcu_read_lock();

	task = pid_task(find_vpid(pid), PIDTYPE_PID);
	if (!task) {
		rcu_read_unlock();
<<<<<<< HEAD
		return 0;               /* invalid pid -> read returns 0 */
	}

	get_task_comm(comm, task);
	EMIT("command = [%s] pid = [%d] state = [%u]\n",
	     comm, task_pid_vnr(task), ti_state(task));
	EMIT("state_name = [%s]\n", ti_state_name(task));

	/* ---- parent ------------------------------------------------- */
	par = rcu_dereference(task->real_parent);
	if (par && par != task && task_tgid_vnr(par) != 0) {
		get_task_comm(pcomm, par);
		EMIT("ppid = [%d] parent_command = [%s]\n",
		     task_tgid_vnr(par), pcomm);
=======
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
>>>>>>> 23f771c28187b4ac3c9f46b2cbf021da7abe366d
	} else {
		EMIT("ppid = [0] parent_command = [-]\n");
	}

<<<<<<< HEAD
	/* ---- ancestors (walk up, then print root first) --------------- */
	{
		struct task_struct *cur = task;

		while (nanc < TI_MAX_ANCESTORS) {
			par = rcu_dereference(cur->real_parent);
			if (!par || par == cur || task_tgid_vnr(par) == 0)
				break;
			anc[nanc++] = par;
			cur = par;
		}
	}

	/* ---- children: processes whose real parent is in our group ----- */
	for_each_process(p) {
		struct task_struct *rp = rcu_dereference(p->real_parent);

		if (p != task->group_leader && rp && rp->tgid == task->tgid)
			nchild++;
	}
	EMIT("nchildren = [%d]\n", nchild);

	for (i = nanc - 1; i >= 0; i--) {
		get_task_comm(pcomm, anc[i]);
		EMIT("ancestor: pid = [%d] command = [%s] state = [%u]\n",
		     task_tgid_vnr(anc[i]), pcomm, ti_state(anc[i]));
	}

	for_each_process(p) {
		struct task_struct *rp = rcu_dereference(p->real_parent);

		if (p == task->group_leader || !rp || rp->tgid != task->tgid)
			continue;
		if (shown >= TI_MAX_CHILDREN)
			break;
		get_task_comm(pcomm, p);
		EMIT("child: pid = [%d] command = [%s] state = [%u]\n",
		     task_tgid_vnr(p), pcomm, ti_state(p));
		shown++;
	}
	if (shown < nchild)
=======
	{
		struct task_struct *current = task;

		while (ancestor_count < TI_MAX_ANCESTORS) {
			parent = rcu_dereference(current->real_parent);
			if (!parent || parent == current ||
			    task_tgid_vnr(parent) == 0)
				break;
			ancestors[ancestor_count++] = parent;
			current = parent;
		}
	}

	for_each_process(process) {
		struct task_struct *real_parent =
			rcu_dereference(process->real_parent);

		if (process != task->group_leader && real_parent &&
		    real_parent->tgid == task->tgid)
			child_count++;
	}
	EMIT("nchildren = [%d]\n", child_count);

	for (i = ancestor_count - 1; i >= 0; i--) {
		get_task_comm(parent_command, ancestors[i]);
		EMIT("ancestor: pid = [%d] command = [%s] state = [%u]\n",
		     task_tgid_vnr(ancestors[i]), parent_command,
		     ti_state(ancestors[i]));
	}

	for_each_process(process) {
		struct task_struct *real_parent =
			rcu_dereference(process->real_parent);

		if (process == task->group_leader || !real_parent ||
		    real_parent->tgid != task->tgid)
			continue;
		if (shown_children >= TI_MAX_CHILDREN)
			break;

		get_task_comm(parent_command, process);
		EMIT("child: pid = [%d] command = [%s] state = [%u]\n",
		     task_tgid_vnr(process), parent_command,
		     ti_state(process));
		shown_children++;
	}
	if (shown_children < child_count)
>>>>>>> 23f771c28187b4ac3c9f46b2cbf021da7abe366d
		EMIT("truncated = [children]\n");

	rcu_read_unlock();
	return len;
}
