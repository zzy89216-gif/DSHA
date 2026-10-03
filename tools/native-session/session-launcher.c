#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/prctl.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

/*
 * Own the isolated session until Java confirms its whole group exited.
 * The child shell may stop itself after publishing its foreground status;
 * keeping this native leader runnable lets parent death end its initial
 * process group even while that shell is stopped. Java separately verifies
 * the full session and retains a durable record if members escaped the group.
 */
static void parent_gone(int signal_number) {
    (void)signal_number;
    kill(-getpid(), SIGKILL);
    _exit(125);
}

int main(int argc, char **argv) {
    if (argc < 2) { fputs("DSHA_SESSION_USAGE\n", stderr); return 125; }
    pid_t original_parent = getppid();
    if (original_parent <= 1) { fputs("DSHA_SESSION_PARENT\n", stderr); return 125; }
    if (setsid() < 0) { perror("DSHA_SESSION_SETSID"); return 125; }

    struct sigaction action = {0};
    action.sa_handler = parent_gone;
    sigemptyset(&action.sa_mask);
    if (sigaction(SIGTERM, &action, NULL) < 0
            || prctl(PR_SET_PDEATHSIG, SIGTERM) < 0) {
        perror("DSHA_SESSION_PARENT_WATCH");
        return 125;
    }
    /* Parent may die between getppid and PR_SET_PDEATHSIG. No guest starts then. */
    if (getppid() != original_parent) parent_gone(SIGTERM);

    pid_t child = fork();
    if (child < 0) { perror("DSHA_SESSION_FORK"); return 125; }
    if (child == 0) {
        struct sigaction ordinary = {0};
        ordinary.sa_handler = SIG_DFL;
        sigemptyset(&ordinary.sa_mask);
        sigaction(SIGTERM, &ordinary, NULL);
        execvp(argv[1], argv + 1);
        int error = errno;
        perror("DSHA_SESSION_EXEC");
        _exit(error == ENOENT ? 127 : 126);
    }

    int status;
    for (;;) {
        if (waitpid(child, &status, 0) == child) break;
        if (errno == EINTR) continue;
        perror("DSHA_SESSION_WAIT");
        break;
    }
    /* An unexpected shell exit must not leave descendants without a leader. */
    kill(-getpid(), SIGKILL);
    _exit(125);
}
