#!/bin/bash

set -eu

function soLong {
  MSG=${1:-No msg}
  echo ${MSG}
  exit 1
}

function trim {
  MSG=${1:-}
  echo ${MSG} | sed -e 's/^ *//; s/ *$//'
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

[ -z "${1:-}" ] && soLong "File list not provided"

SHOPPINGLIST=$1

OLDIFS=$IFS
IFS='!'
cat ${SHOPPINGLIST} | sed -e 's/#.*//' | while read URL FILENAME CANCELLED
do
  if [ "${URL}" = "" ]
  then
    continue
  fi
  CURURL=$(trim ${URL})
  CURFILENAME=$(trim ${FILENAME})
  CURCANCELLED=$(trim ${CANCELLED})

  FINALFILENAME="${DATADIR}/${CURFILENAME}"
  if [[ ${CURFILENAME} =~ ^/ ]]
  then
    FINALFILENAME=${CURFILENAME}
  fi

  if [ "${CURCANCELLED}" = "yes" ]
  then
    if [ -f ${FINALFILENAME} ]
    then
      continue
    fi
  fi
  echo "URL='${URL}' -> '${CURURL}'"
  echo "FILENAME='${FILENAME}' -> '${CURFILENAME}' -> '${FINALFILENAME}'"
  echo "TERMINADO='${CANCELLED}' -> '${CURCANCELLED}'"

  BASEFILENAME=$(dirname ${FINALFILENAME})
  mkdir -pv ${BASEFILENAME}

  python ${WRKDIR}/bin/downloadRSSfeed.py -u ${CURURL} -p -m 0 -o ${FINALFILENAME}
  echo "------------------------------------"
done
IFS=$OLDIFS

##Programas terminados
#python ${WRKDIR}/bin/downloadRSSfeed.py -u http://www.rtve.es/api/programas/33831/audios.rss -p -m 0 -o ${DATADIR}/RSS-DivanCabala.rss
#python ${WRKDIR}/bin/downloadRSSfeed.py -u http://www.rtve.es/api/programas/89370/audios.rss -p -m 0 -o ${DATADIR}/RSS-HoraBach.rss
#python ${WRKDIR}/bin/downloadRSSfeed.py -u http://www.rtve.es/api/programas/23353/audios.rss -p -m 0 -o ${DATADIR}/RSS-MusAntigua.rss
#python ${WRKDIR}/bin/downloadRSSfeed.py -u http://www.rtve.es/api/programas/101530/audios.rss -p -m 0 -o ${DATADIR}/RSS-MusYSubs.rss
#
#
#
#python ${WRKDIR}/bin/downloadRSSfeed.py -u http://www.rtve.es/api/programas/118630/audios.rss -p -m 0 -o ${DATADIR}/RSS-GranRepertorio.rss
#python ${WRKDIR}/bin/downloadRSSfeed.py -u http://www.rtve.es/api/programas/22332/audios.rss -p -m 0 -o ${DATADIR}/RSS-MelPizarra.rss
#python ${WRKDIR}/bin/downloadRSSfeed.py -u http://www.rtve.es/api/programas/40382/audios.rss -p -m 0 -o ${DATADIR}/RSS-MusYSig.rss
#python ${WRKDIR}/bin/downloadRSSfeed.py -u http://www.rtve.es/api/programas/84390/audios.rss -p -m 0 -o ${DATADIR}/RSS-SicutLuna.rss
#python ${WRKDIR}/bin/downloadRSSfeed.py -u http://www.rtve.es/api/programas/111690/audios.rss -p -m 0 -o ${DATADIR}/RSS-TranviaBroadway.rss
#python ${WRKDIR}/bin/downloadRSSfeed.py -u http://www.rtve.es/api/programas/128614/audios.rss -p -m 0 -o ${DATADIR}/RSS-ArmoniasVocales.rss
#python ${WRKDIR}/bin/downloadRSSfeed.py -u http://www.rtve.es/api/programas/1000690/audios.rss -p -m 0 -o ${DATADIR}/RSS-BachCualquierHora.rss
