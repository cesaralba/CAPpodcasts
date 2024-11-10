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
    CANCELLEDSTR=${CURCANCELLED}
  else
    CANCELLEDSTR="no"
  fi

  BASEFILENAME=$(dirname ${FINALFILENAME})
  mkdir -pv ${BASEFILENAME}

  python ${WRKDIR}/bin/downloadRSSfeed.py -u ${CURURL} -p -m 0 -o ${FINALFILENAME}
  echo "Descargado '${CURURL}' -> '${FINALFILENAME}' (cancelled? ${CANCELLEDSTR})"
done
IFS=$OLDIFS
