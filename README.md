# IG-BL-firmware-update
This project provides and example lambda to update BL654 firmware. 

firmware update are triggered by the topic: fwloader/trigger/<core name>
Here is the example JSON data 
```
{
  "update-file": "QSPI_BL_SD_SB_PK_Build_13.uwf"
}
```
