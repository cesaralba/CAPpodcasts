#!/bin/bash

set -eu

function soLong {
  MSG=${1:-No msg}
  echo ${MSG}
  exit 1
}

CONFIGFILE=${DEVSMCONFIGFILE:-/etc/sysconfig/RSSretriever}
[ -f ${CONFIGFILE} ] && source ${CONFIGFILE}

if [ ${CS_DEBUGSCRIPTS:-0} = 1 ]
then
  set -vx
fi

ME="$(readlink -e $0)"
HEREDIR=$(cd "$(dirname ${ME})" && pwd )
BASEDIR=$(cd "${HEREDIR}/../" && pwd )
TODAY=$(date '+%Y%m%d%H%M')

if [ -n "${CS_ROOTWRK}" ] ; then
  ROOTDATA=${CS_ROOTWRK}
else
  ROOTDATA=${BASEDIR}
fi

[ "x${CS_REPO}" = "x" ] && soLong "ORROR: No se ha suministrado valor para CS_REPO. Adios."

WRKDIR="${ROOTDATA}/wrk"

DATADIR=${CS_DATADIR:-${ROOTDATA}/feeds}

[ -d ${WRKDIR} ] || soLong "ORROR: No se encuentra código descargado. Pruebe a ejecutar ${HEREDIR}/buildVENV.sh . Adios."

VENV=${VENVHOME:-"${BASEDIR}/venv"}
ACTIVATIONSCR="${VENV}/bin/activate"

if [ -f "${ACTIVATIONSCR}" ] ; then
  source "${ACTIVATIONSCR}"
else
  soLong "ORROR: Incapaz de encontrar activador de virtualenv. Pruebe a ejecutar ${HEREDIR}/buildVENV.sh . Adios."
fi
mkdir -pv ${DATADIR}

export PYTHONPATH="${PYTHONPATH:-}:${WRKDIR}"

#Programas terminados
python ${WRKDIR}/bin/downloadRSSfeed.py -u http://www.rtve.es/api/programas/33831/audios.rss -p -m 0 -o ${DATADIR}/RSS-DivanCabala.rss
python ${WRKDIR}/bin/downloadRSSfeed.py -u http://www.rtve.es/api/programas/89370/audios.rss -p -m 0 -o ${DATADIR}/RSS-HoraBach.rss
python ${WRKDIR}/bin/downloadRSSfeed.py -u http://www.rtve.es/api/programas/23353/audios.rss -p -m 0 -o ${DATADIR}/RSS-MusAntigua.rss
python ${WRKDIR}/bin/downloadRSSfeed.py -u http://www.rtve.es/api/programas/101530/audios.rss -p -m 0 -o ${DATADIR}/RSS-MusYSubs.rss



python ${WRKDIR}/bin/downloadRSSfeed.py -u http://www.rtve.es/api/programas/118630/audios.rss -p -m 0 -o ${DATADIR}/RSS-GranRepertorio.rss
python ${WRKDIR}/bin/downloadRSSfeed.py -u http://www.rtve.es/api/programas/22332/audios.rss -p -m 0 -o ${DATADIR}/RSS-MelPizarra.rss
python ${WRKDIR}/bin/downloadRSSfeed.py -u http://www.rtve.es/api/programas/40382/audios.rss -p -m 0 -o ${DATADIR}/RSS-MusYSig.rss
python ${WRKDIR}/bin/downloadRSSfeed.py -u http://www.rtve.es/api/programas/84390/audios.rss -p -m 0 -o ${DATADIR}/RSS-SicutLuna.rss
python ${WRKDIR}/bin/downloadRSSfeed.py -u http://www.rtve.es/api/programas/111690/audios.rss -p -m 0 -o ${DATADIR}/RSS-TranviaBroadway.rss
python ${WRKDIR}/bin/downloadRSSfeed.py -u http://www.rtve.es/api/programas/128614/audios.rss -p -m 0 -o ${DATADIR}/RSS-ArmoniasVocales.rss
python ${WRKDIR}/bin/downloadRSSfeed.py -u http://www.rtve.es/api/programas/1000690/audios.rss -p -m 0 -o ${DATADIR}/RSS-BachCualquierHora.rss
