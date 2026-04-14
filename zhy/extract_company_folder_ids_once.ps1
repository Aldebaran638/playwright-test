$inputPath = "zhy\data\output\2026-01\competitor_patent_pipeline\competitor_folder_mapping_raw.json"
$outputPath = "zhy\data\output\2026-01\competitor_patent_pipeline\company_folder_ids.json"

$folderPattern = '"folder_id"\s*:\s*"([0-9a-f]{32})"'
$parentPattern = '"parent_id"\s*:\s*"([^"]+)"'

$lines = Get-Content -Path $inputPath

$validFolderIds = @{}
foreach ($line in $lines) {
    if ($line -match $folderPattern) {
        $validFolderIds[$matches[1]] = $true
    }
}

$result = New-Object System.Collections.Generic.List[string]
$currentFolderId = $null

foreach ($line in $lines) {
    if ($line -match $folderPattern) {
        $currentFolderId = $matches[1]
        continue
    }

    if ($currentFolderId -and $line -match $parentPattern) {
        $parentId = $matches[1]
        if ($parentId -ne "-root" -and $validFolderIds.ContainsKey($parentId)) {
            $result.Add($currentFolderId)
        }
        $currentFolderId = $null
    }
}

$result | ConvertTo-Json | Set-Content -Path $outputPath -Encoding utf8
Write-Host "saved $($result.Count) company folder ids -> $outputPath"
