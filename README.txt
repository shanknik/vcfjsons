Some basic instructions to get you by


###########################################################################
To get a bearer token
###########################################################################

curl --location --request POST 'https://sddcmanagerFQDN/v1/tokens' \
--header 'Content-Type: application/json' \
--header 'Accept: application/json' \
--data-raw '{
  "username" : "administrator@vsphere.local",
  "password" : "VMware123!"
}'

###########################################################################
To get all unassigned usable hosts:
###########################################################################
GET request to https://sddcManagerFQDN/v1/hosts?status=UNASSIGNED_USEABLE

###########################################################################
Validate cluster stretch json, using validateClusterStretch.json:
###########################################################################

POST https://sddcManagerFQDN/v1/clusters/id/validations


###########################################################################
To stretch the cluster after validation using clusterStretch.json:
###########################################################################

PATCH https://sddcManagerFQDN/v1/clusters/id/validations