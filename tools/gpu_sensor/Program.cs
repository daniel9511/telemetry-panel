using System;
using System.Globalization;
using LibreHardwareMonitor.Hardware;

var computer = new Computer { IsGpuEnabled = true };
computer.Open();

float gpuLoad = 0f;
float gpuTemp = 0f;

foreach (var hw in computer.Hardware)
{
    if (hw.HardwareType is not (HardwareType.GpuAmd or HardwareType.GpuNvidia or HardwareType.GpuIntel))
        continue;

    hw.Update();

    foreach (var sensor in hw.Sensors)
    {
        if (sensor.Value is null) continue;

        if (sensor.SensorType == SensorType.Load && sensor.Name.Contains("GPU Core", StringComparison.OrdinalIgnoreCase))
            gpuLoad = MathF.Round(sensor.Value.Value, 1);

        if (sensor.SensorType == SensorType.Temperature && sensor.Name.Contains("GPU", StringComparison.OrdinalIgnoreCase))
            gpuTemp = MathF.Round(sensor.Value.Value, 1);
    }
}

computer.Close();

Console.WriteLine($"{{\"gpu_usage\":{gpuLoad.ToString("F1", System.Globalization.CultureInfo.InvariantCulture)},\"gpu_temp\":{gpuTemp.ToString("F1", System.Globalization.CultureInfo.InvariantCulture)}}}");
