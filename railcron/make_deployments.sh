#!/bin/bash

# Location of configuration file to use outside of built deployment package
CFGLOC="/tmp"

if [ -z "$1" ] ; then

prefect deployment build flows/opendata.py:atoc_timetable -n ATOC_TT -t daily -t ATOC -t timetable --output deployments/atoc.yaml
prefect deployment build flows/opendata.py:incidents -n INCIDENTS -t daily -t Incidents -t XML --output deployments/incidents.yaml

prefect deployment build flows/hda_data.py:hda_data -n HDA_DATA -t daily -t NR -t HDA --output deployments/hda.yaml

prefect deployment build flows/a51_archive.py:a51_td -n A51_TD -t daily -t A51 -t TD  --output deployments/a51_td.yaml
prefect deployment build flows/a51_archive.py:a51_trust -n A51_TRUST -t daily -t A51 -t TRUST  --output deployments/a51_trust.yaml
prefect deployment build flows/a51_archive.py:a51_darwin -n A51_DARWIN -t daily -t A51 -t DARWIN --output deployments/a51_darwin.yaml

prefect deployment build flows/nrdp_data.py:nrdp_darwin_timetable -n DARWIN_TT -t daily -t NRDP -t DARWIN -t timetable --output deployments/nrdp_darwin.yaml
prefect deployment build flows/nrdp_data.py:nrdp_location -n LOCATIONS -t daily -t NRDP -t reference -t location --output deployments/nrdp_loc.yaml
prefect deployment build flows/nrdp_data.py:nrdp_ref -n NRDP_REF -t daily -t NRDP -t reference --output deployments/nrdp_ref.yaml
prefect deployment build flows/nrdp_data.py:nrdp_timetable -n NRDP_TT  -t daily -t NRDP -t timetable --output deployments/nrdp_timetable.yaml
prefect deployment build flows/nrdp_data.py:nrdp_logs -n NRDP_LOGS -t daily -t NRDP -t DARWIN -t logs --output deployments/nrdp_logs.yaml

prefect deployment build flows/singlefile.py:data_smart -n SMART -t daily -t SMART -t reference  --output deployments/smart.yaml
prefect deployment build flows/singlefile.py:data_corpus -n CORPUS -t daily -t CORPUS -t reference --output deployments/corpus.yaml
prefect deployment build flows/singlefile.py:data_tps -n TPS -t daily -t TPS -t reference  --output deployments/tps.yaml

prefect deployment build flows/singlefile.py:sched_full_cif -n FULL_CIF -t daily -t schedule -t CIF -t full --output deployments/full_cif.yaml
prefect deployment build flows/singlefile.py:sched_update_cif -n UPDATE_CIF -t daily -t schedule -t CIF -t update --output deployments/update_cif.yaml
prefect deployment build flows/singlefile.py:sched_full_json -n FULL_JSON -t daily -t schedule -t JSON -t full --output deployments/full_json.yaml
prefect deployment build flows/singlefile.py:sched_update_json -n UPDATE_JSON -t daily -t schedule -t JSON -t update --output deployments/update_json.yaml
prefect deployment build flows/singlefile.py:sched_full_freight -n FULL_FREIGHT -t daily -t schedule -t JSON -t full -t freight --output deployments/full_freight.yaml
prefect deployment build flows/singlefile.py:sched_update_freight -n UPDATE_FREIGHT -t daily -t schedule -t JSON -t update -t freight --output deployments/update_freight.yaml

cd deployments

for x in *.yaml ; do sed -i "s# env: {}# env: {'FETCH_CFG': '$CFGLOC'}#" $x ; done
## Could also use the Prefect UI to set schedules
# for x in *.yaml ; do
#  sed -i "s# schedule: {}# schedule: {'cron': '35 15 * * *', 'timezone': 'Europe/London', 'day_or': True} #" $x
# done

cd ..

else

   for x in `ls -1 ./deployments/*.yaml` ; do
     prefect deployment apply $x
   done

fi

## cmd to manually run a deployment (or through the UI)
#  prefect deployment run  <flow name>/<deploy name>
