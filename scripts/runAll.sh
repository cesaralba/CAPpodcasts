#!/bin/bash

set -eu

#https://www.putorius.net/lock-files-bash-scripts.html
LOCKFILE=/tmp/actualizaRSSPodcasts.lock
if { set -C; >${LOCKFILE}; }; then
       trap "rm -f ${LOCKFILE}" EXIT
else
       echo "Lock file '${LOCKFILE} exists… exiting"
       exit
fi


BASEDIR=$(cd "$(dirname $(readlink -e $0))" && pwd )

CONFIGFILE=${DEVSMCONFIGFILE:-/etc/sysconfig/RSSretriever}
[ -f ${CONFIGFILE} ] && source ${CONFIGFILE}

bash ${BASEDIR}/buildDataTree.sh
bash ${BASEDIR}/buildVENV.sh
bash ${BASEDIR}/checkScripts.sh || true
bash ${BASEDIR}/retrieveRSS.sh
