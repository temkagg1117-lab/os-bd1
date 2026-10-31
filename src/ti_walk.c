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
 */
#include <linux/kernel.h>
#include <linux/sched.h>
#include <linux/sched/signal.h>
#include <linux/pid.h>
#include <linux/rcupdate.h>
#include <linux/version.h>
#include "ti_walk.h"

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
	struct task_struct *task, *par, *p;
	char comm[TASK_COMM_LEN], pcomm[TASK_COMM_LEN];
	struct task_struct *anc[TI_MAX_ANCESTORS];
	int nanc = 0, nchild = 0, shown = 0, i, len = 0;

	rcu_read_lock();

	task = pid_task(find_vpid(pid), PIDTYPE_PID);
	if (!task) {
		rcu_read_unlock();
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
	} else {
		EMIT("ppid = [0] parent_command = [-]\n");
	}

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
		EMIT("truncated = [children]\n");

	rcu_read_unlock();
	return len;
}
