# Archive internal-only documents out of the public repo tree.
# MOVE (not delete) into a private archive outside the repo, then untrack the
# ones git was tracking. Writes a manifest for one-command restore.
$root  = 'C:\Code\source-code\openmd'
$arch  = Join-Path $env:USERPROFILE '<private-archive>\internal_docs'

New-Item -ItemType Directory -Force -Path $arch | Out-Null

# group label -> repo-relative paths
$plan = [ordered]@{
    'named_by_user' = @(
        'doc/scenario_redesign_proposal_to_teacher.md',
        'doc/collaboration_plan_september.md',
        'doc/HANDOFF_MDAD006.md',
        'doc/engine_defects_for_engineering.md',
        'doc/link_issue_brief.md',
        'code/eval/scenario_redesign_proposal_to_teacher.md',
        'code/eval/engine_defects_for_engineering.md',
        'code/eval/link_issue_brief.md',
        'code/eval/HANDOFF_MDAD006.md',
        'code/eval/HANDOFF_AGENT_CTX.md',
        'code/eval/HANDOFF_TO_CODEX.md',
        'code/eval/HANDOFF_TO_DEEPSEEK.md',
        'code/eval/LLMRL_HANDOFF.md',
        'code/eval/RESUME_HERE.md',
        'code/eval/PURE_GRAPH_HANDOFF.md'
    )
    'same_class_sibling' = @(
        'code/eval/engine_internal_fairness_audit.md',
        'code/eval/ie_set_experiment_s1.md',
        'code/eval/llm_method_assessment_report.md',
        'code/eval/md_ad_006_engine_handover.md',
        'code/eval/md_ad_006_fcd0fab_alignment.md',
        'code/eval/simulation_fairness_audit.md',
        'code/eval/LLM_RL_QUALITY_STATUS.md'
    )
    'superseded_run_record' = @(
        'code/eval/ammo2_regime_results.md',
        'code/eval/md_ad_006_civilian_roe.md',
        'code/eval/md_ad_006_engine_fixes.md',
        'code/eval/md_ad_006_gap_plan.md',
        'code/eval/md_ad_006_three_arm_experiment.md',
        'code/eval/md_ad_006_three_arm_f4_report.md',
        'code/eval/three_methods_reproduction_results.md'
    )
}

$rows = New-Object System.Collections.ArrayList
$moved = 0; $bytes = 0; $trackedHits = @()

foreach ($group in $plan.Keys) {
    foreach ($rel in $plan[$group]) {
        $src = Join-Path $root ($rel -replace '/', '\')
        if (-not (Test-Path -LiteralPath $src -PathType Leaf)) {
            Write-Output ("  skip (absent): {0}" -f $rel)
            continue
        }
        # was git tracking it?
        Push-Location $root
        git ls-files --error-unmatch $rel *> $null
        $isTracked = ($LASTEXITCODE -eq 0)
        Pop-Location

        $len = (Get-Item -LiteralPath $src).Length
        $dst = Join-Path $arch ($rel -replace '/', '\')
        $dir = Split-Path $dst -Parent
        if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }

        Move-Item -LiteralPath $src -Destination $dst -Force -ErrorAction Stop
        if ($isTracked) {
            Push-Location $root
            git rm --cached --quiet -- $rel | Out-Null
            Pop-Location
            $trackedHits += $rel
        }
        [void]$rows.Add([pscustomobject]@{
            group = $group; rel = $rel; bytes = $len; was_tracked = $isTracked
        })
        $moved++; $bytes += $len
    }
}

$manifest = Join-Path $arch '_archive_manifest.csv'
$rows | Export-Csv -Path $manifest -NoTypeInformation -Encoding UTF8

Write-Output ""
Write-Output ("archived: {0} files  {1:n1} KB" -f $moved, ($bytes / 1KB))
Write-Output ("untracked from git: {0}" -f ($trackedHits -join ', '))
Write-Output ("archive root: {0}" -f $arch)
Write-Output ("manifest: {0}" -f $manifest)
