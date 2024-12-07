import numpy as np

DATA_SAMPLE_RATE = 20e6
DESIRED_SAMPLE_RATE = 122.88e6


def upsample_data(data, original_rate, new_rate):
    """
    Upsample the data
    """
    # Original data points
    duration = (
        len(data) / original_rate
    )  # Calculate signal duration from data and sample rate

    # Generate original time points
    t_original = np.linspace(0, duration, len(data), endpoint=False)

    # Generate target time points
    num_target_points = int(new_rate * duration)
    t_target = np.linspace(0, duration, num_target_points, endpoint=False)

    # Perform interpolation
    resampled_data = np.interp(t_target, t_original, data)

    return resampled_data
