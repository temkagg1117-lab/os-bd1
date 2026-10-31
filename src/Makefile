# Build:  make            (needs kernel headers of the running kernel)
# Load:   sudo insmod task_info.ko
# Clean:  make clean
obj-m := task_info.o
task_info-y := ti_main.o ti_walk.o

KDIR ?= /lib/modules/$(shell uname -r)/build

all:
	$(MAKE) -C $(KDIR) M=$(CURDIR) modules

clean:
	$(MAKE) -C $(KDIR) M=$(CURDIR) clean
