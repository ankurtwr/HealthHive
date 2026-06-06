# scripts/ocr.ps1
param (
    [string]$ImagePath
)

if (-not $ImagePath) {
    Write-Error "Please specify -ImagePath"
    exit 1
}

$ImagePath = Resolve-Path $ImagePath
if (-not (Test-Path $ImagePath)) {
    Write-Error "File not found: $ImagePath"
    exit 1
}

try {
    # 1. Load Assemblies
    Add-Type -AssemblyName System.Runtime.WindowsRuntime
    [void][Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
    [void][Windows.Storage.FileAccessMode, Windows.Storage, ContentType = WindowsRuntime]
    [void][Windows.Storage.Streams.IRandomAccessStream, Windows.Storage, ContentType = WindowsRuntime]
    [void][Windows.Graphics.Imaging.SoftwareBitmap, Windows.Foundation, ContentType = WindowsRuntime]
    [void][Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation, ContentType = WindowsRuntime]
    [void][Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
    [void][Windows.Media.Ocr.OcrResult, Windows.Foundation, ContentType = WindowsRuntime]

    # 2. Reflect GetAwaiter for IAsyncOperation`1
    $getAwaiter = [System.WindowsRuntimeSystemExtensions].GetMember('GetAwaiter').Where({ 
        $PSItem.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' 
    }, 'First')[0]

    function Invoke-Async {
        param($AsyncOp, $ResultType)
        $genericGetAwaiter = $getAwaiter.MakeGenericMethod($ResultType)
        $awaiter = $genericGetAwaiter.Invoke($null, @($AsyncOp))
        return $awaiter.GetResult()
    }

    # 3. Open File
    $storageFile = Invoke-Async ([Windows.Storage.StorageFile]::GetFileFromPathAsync($ImagePath)) ([Windows.Storage.StorageFile])

    # 4. Open Stream
    $stream = Invoke-Async ($storageFile.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])

    # 5. Decode Image
    $decoder = Invoke-Async ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
    $softwareBitmap = Invoke-Async ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])

    # 6. Initialize OCR Engine
    $ocrEngine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
    if ($ocrEngine -eq $null) {
        Write-Error "OCR engine could not be initialized. Check language packs."
        exit 1
    }

    # 7. Perform OCR
    $ocrResult = Invoke-Async ($ocrEngine.RecognizeAsync($softwareBitmap)) ([Windows.Media.Ocr.OcrResult])

    # Output text
    Write-Output "RECOGNIZED:$($ocrResult.Text)"

    # Dispose stream
    $stream.Dispose()
    exit 0
}
catch {
    Write-Error "OCR Execution failed: $_"
    exit 1
}
