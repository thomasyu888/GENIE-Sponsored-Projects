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
   val production
   val use_grs

   output:
   stdout

   script:
   if (production && use_grs) {
      """
      geniesp $cohort $release \
         --upload \
         --cbioportal /usr/src/cbioportal \
         --production \
         --use-grs
      """
   } else if (production && !use_grs){
      """
      geniesp $cohort $release \
         --upload \
         --cbioportal /usr/src/cbioportal \
         --production
      """
   } else if (!production && use_grs){
      """
      geniesp $cohort $release \
         --upload \
         --cbioportal /usr/src/cbioportal \
         --use-grs
      """
   } else {
      """
      geniesp $cohort $release \
         --upload \
         --cbioportal /usr/src/cbioportal \
      """
   }
}

workflow {
   params.cohort = 'NSCLC' // Default
   params.release = '1.1-consortium'  // Default
   params.production = false
   params.use_grs = false

   // Check if cohort is part of allowed cohort list
   def allowed_cohorts = ["BLADDER", "BrCa", "CRC", "ESOPHAGO", "MELANOMA", "NSCLC", "OVARIAN", "PANC", "Prostate", "RENAL"]
   if (!allowed_cohorts.contains(params.cohort)) {exit 1, 'Invalid cohort name'}

   ch_cohort = Channel.value(params.cohort)
   ch_release = Channel.value(params.release)
   ch_production = Channel.value(params.production)
   ch_use_grs = Channel.value(params.use_grs)

   cBioPortalExport(ch_cohort, ch_release, ch_production, ch_use_grs)
}
