#include <stdio.h>
#include <sys/utsname.h>

int main(void) {
    struct utsname info;
    if (uname(&info) != 0) { perror("uname"); return 1; }
    printf("QB560D-EU training application 1.0.0\n");
    printf("kernel=%s architecture=%s\n", info.release, info.machine);
    return 0;
}
