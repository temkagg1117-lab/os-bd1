// SPDX-License-Identifier: GPL-2.0
/*
 * ti_main.c - /proc interface of the task-information module (Member 1)
 *
 *   echo "1395" > /proc/pid     store the pid to inspect
 *   cat /proc/pid               report for that pid (see ti_walk.c)
 *
 * Module parameter  proc_name=<name>  changes the /proc entry name
 * (default "pid", as in the textbook).
 */
#include <linux/init.h>
#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/proc_fs.h>
#include <linux/uaccess.h>
#include <linux/slab.h>
#include <linux/mutex.h>
#include <linux/string.h>
#include <linux/threads.h>
#include <linux/version.h>
#include "ti_walk.h"

#define TI_MAX_INPUT 16        /* longest accepted write, incl. newline */
#define TI_OUT_SIZE  16384     /* report buffer                        */

static char *proc_name = "pid";
module_param(proc_name, charp, 0444);
MODULE_PARM_DESC(proc_name, "name of the /proc entry (default: pid)");

static DEFINE_MUTEX(ti_lock);
static long ti_pid;            /* 0 = nothing selected yet */
static struct proc_dir_entry *ti_entry;

/* Figure 3.37 of the textbook, extended with validation. */
static ssize_t ti_write(struct file *file, const char __user *usr_buf,
			size_t count, loff_t *pos)
{
	char *k_mem;
	long val;
	int rv;

	if (count == 0 || count > TI_MAX_INPUT) {
		pr_warn("task_info: input length %zu rejected (1..%d)\n",
			count, TI_MAX_INPUT);
		return -EINVAL;
	}

	k_mem = kmalloc(count + 1, GFP_KERNEL);
	if (!k_mem)
		return -ENOMEM;

	if (copy_from_user(k_mem, usr_buf, count)) {
		kfree(k_mem);
		return -EFAULT;
	}
	k_mem[count] = '\0';

	rv = kstrtol(strim(k_mem), 10, &val);
	kfree(k_mem);
	if (rv) {
		pr_warn("task_info: input is not a decimal number\n");
		return -EINVAL;
	}
	if (val <= 0 || val > PID_MAX_LIMIT) {
		pr_warn("task_info: pid %ld out of range 1..%d\n",
			val, PID_MAX_LIMIT);
		return -EINVAL;
	}

	mutex_lock(&ti_lock);
	ti_pid = val;
	mutex_unlock(&ti_lock);
	return count;
}

static ssize_t ti_read(struct file *file, char __user *usr_buf,
		       size_t count, loff_t *pos)
{
	char *buf;
	long pid;
	int len;
	ssize_t rv;

	mutex_lock(&ti_lock);
	pid = ti_pid;
	mutex_unlock(&ti_lock);

	if (pid == 0) {
		pr_info("task_info: no pid selected yet\n");
		return 0;
	}

	buf = kmalloc(TI_OUT_SIZE, GFP_KERNEL);
	if (!buf)
		return -ENOMEM;

	len = ti_build_report((pid_t)pid, buf, TI_OUT_SIZE);
	if (len == 0)
		pr_info("task_info: no task with pid %ld\n", pid);

	rv = simple_read_from_buffer(usr_buf, count, pos, buf, len);
	kfree(buf);
	return rv;
}

#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 6, 0)
static const struct proc_ops ti_ops = {
	.proc_read  = ti_read,
	.proc_write = ti_write,
};
#else
static const struct file_operations ti_ops = {
	.owner = THIS_MODULE,
	.read  = ti_read,
	.write = ti_write,
};
#endif

static int __init ti_init(void)
{
	/* 0666: the report only holds data that /proc/<pid>/stat already
	 * shows to every user, so unprivileged users may write the pid. */
	ti_entry = proc_create(proc_name, 0666, NULL, &ti_ops);
	if (!ti_entry) {
		pr_err("task_info: cannot create /proc/%s\n", proc_name);
		return -ENOMEM;
	}
	pr_info("task_info: loaded, /proc/%s ready\n", proc_name);
	return 0;
}

static void __exit ti_exit(void)
{
	remove_proc_entry(proc_name, NULL);
	pr_info("task_info: unloaded\n");
}

module_init(ti_init);
module_exit(ti_exit);

MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("F.CSM302 BD1 - Task information via /proc/pid");
MODULE_AUTHOR("OS BD1 team");
