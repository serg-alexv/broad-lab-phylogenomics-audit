function Add-QcEtaPresentationV1($Lines,[string]$Root,[int]$Width){
    try{
        $Path=Join-Path $Root 'state\monitor_qc_eta_v1\current.json'
        $Value=Read-SmallDisplayJsonV42 $Path
        if($Value.schema -ne 'TREE2_MONITOR_QC_ETA_V1'){throw 'Unknown estimator schema'}
        $Age=([datetime]::UtcNow-(Get-UtcDate $Value.updated_utc)).TotalSeconds
        if($Age -gt 95){Add-Wrapped $Lines ('QC ESTIMATOR STALE: last sample '+(Format-Age $Value.updated_utc)+'; counters/forecast below are saved observations.') ($Width-2)}
        $C=$Value.campaign;$B=$Value.batch;$E=$Value.eta
        $Lines.Add('QC COMPLETION AND ETA (method estimates; final panel acceptance is separate):')
        Add-Wrapped $Lines ('Accepted '+$C.accepted_supported+' / '+$C.source_supported+'; saved feature validated/reused '+$C.saved_validated_reused+'; all method-validated including saved '+$C.all_method_validated_including_saved+'.') ($Width-2)
        Add-Wrapped $Lines ('New QC feature-validated '+$C.new_genomes_feature_validated+' / '+$C.bulk_total+'; complete-cohort checkpointed '+$C.new_bulk_cohort_checkpointed+' / '+$C.bulk_total+'; externally accepted new '+$C.new_bulk_accepted+'.') ($Width-2)
        Add-Wrapped $Lines ('Remaining work '+$C.remaining_processing_and_history+' = bulk '+($C.bulk_total-$C.new_genomes_feature_validated)+' + history reviews '+$C.historical_review_remaining+'. Batch '+$B.number+' / '+$B.total+': '+$B.genomes+' new genomes + '+$B.controls+' actual search control(s); feature checks '+$B.features_validated_in_current_batch+' / '+$B.genomes+'.') ($Width-2)
        $Elapsed=if($null -ne $B.phase_elapsed_seconds){'{0:N1} min' -f ([double]$B.phase_elapsed_seconds/60)}else{'not available'}
        Add-Wrapped $Lines ('Phase '+$B.phase+'; elapsed '+$Elapsed+'; outcome '+$B.phase_status+'; queue '+$Value.queue.status+' / local controller '+$Value.queue.dispatcher_status+'.') ($Width-2)
        Add-Wrapped $Lines ('ETA: '+$E.display_text) ($Width-2)
        if($E.finish_msk){$Lines.Add('Estimated bulk finish: '+$E.finish_msk+'; five historical reviews/final closure are extra.')}
        if($E.provisional_reference.display_text){Add-Wrapped $Lines ('CONDITIONAL SEARCH-ONLY SCENARIOS (not forecast): '+$E.provisional_reference.display_text) ($Width-2)}
        foreach($Warning in @($Value.budgets.diagnostics)){Add-Wrapped $Lines ('BUDGET DIAGNOSTIC ONLY: '+$Warning) ($Width-2)}
        $Lines.Add('48-hour context/scientific allowances are limits, not completion estimates. Updates every30s without AI calls.')
        $script:EtaLast=$Value
    }catch{Add-Wrapped $Lines ('QC COUNTER / ETA OBSERVATION UNAVAILABLE: '+$_.Exception.Message+'; no completion or rate inferred.') ($Width-2)}
}
