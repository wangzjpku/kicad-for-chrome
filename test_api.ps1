$body = @{
    requirements = "设计一个5V稳压电源电路"
    answers = @{
        input_voltage = "220V"
    }
    mode = "schematic_only"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:8001/api/v1/ai/analyze" -Method POST -Body $body -ContentType "application/json"
$response | ConvertTo-Json -Depth 10
