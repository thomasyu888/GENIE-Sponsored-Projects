#!/usr/bin/env nextflow
nextflow.enable.dsl=2

/*
Run cBioPortal Export
*/
process cBioPortalExport {
   container 'sagebionetworks/geniesp'
   secret 'SYNAPSE_AUTH_TOKEN'

   input:
   val cohort
   val release
   val upload
   val production

   output:
   stdout

   script:
   if (production) {
      """
      geniesp $cohort $release \
         --upload \
         --cbioportal /usr/src/cbioportal \
         --production
      """
   } else {
      """
      geniesp $cohort $release \
         --upload \
         --cbioportal /usr/src/cbioportal
      """
   }
}

workflow {
   params.cohort = 'NSCLC' // Default
   params.release = '1.1-consortium'  // Default
   params.upload = false  // Default
   params.production = false

   // Check if cohort is part of allowed cohort list
   def allowed_cohorts = ["BLADDER", "BrCa", "CRC", "NSCLC", "PANC", "Prostate"]
   if (!allowed_cohorts.contains(params.cohort)) {exit 1, 'Invalid cohort name'}

   ch_cohort = Channel.value(params.cohort)
   ch_release = Channel.value(params.release)
   ch_upload = Channel.value(params.upload)
   ch_production = Channel.value(params.production)

   cBioPortalExport(ch_cohort, ch_release, ch_upload, ch_production)
}
