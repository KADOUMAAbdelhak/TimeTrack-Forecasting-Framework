# Hierarchy comparison (development)

Fingerprint: `bf06dc0e7fe6ff5e`

| hierarchy                | method       |   mean_top_mae_rel |   mean_coherence |   mean_worst_child |   frac_coherent |
|:-------------------------|:-------------|-------------------:|-----------------:|-------------------:|----------------:|
| bond0_transmitted_acamas | bottom_up_nn |           0.99476  |      0           |       48.162       |        1        |
| bond0_transmitted_acamas | mint         |           0.997549 |      0           |       48.2907      |        1        |
| bond0_transmitted_acamas | wls          |           0.997549 |      0           |       48.2907      |        1        |
| bond0_transmitted_acamas | ols          |           0.9984   |      0           |       48.3388      |        1        |
| bond0_transmitted_acamas | independent  |           1        |      3.55202     |       48.4184      |        0.222222 |
| bond0_transmitted_acamas | top_down     |           1        |      1.65848e-12 |       48.4062      |        1        |
| bond0_transmitted_acamas | bottom_up    |           1.00016  |      0           |       48.4184      |        1        |
| bond0_transmitted_acamas | ols_nn       |           1.00225  |      0           |       48.1047      |        1        |
| cpu_core_weighted        | mint         |           0.940167 |      0           |        3.193       |        1        |
| cpu_core_weighted        | wls          |           0.944446 |      0           |        3.23107     |        1        |
| cpu_core_weighted        | bottom_up_nn |           0.948941 |      0           |        3.09758     |        1        |
| cpu_core_weighted        | bottom_up    |           0.953154 |      0           |        3.1345      |        1        |
| cpu_core_weighted        | ols          |           0.982197 |      0           |        3.17326     |        1        |
| cpu_core_weighted        | independent  |           1        |    103.385       |        3.1345      |        0        |
| cpu_core_weighted        | top_down     |           1        |      1.03131e-12 |        3.18416     |        1        |
| disk_ud                  | independent  |           1        |      1.59768e+10 |        1.51871e+10 |        0.333333 |
| disk_ud                  | top_down     |           1        |      5.11363e-05 |        1.36502e+10 |        1        |
| disk_ud                  | ols          |           1.20536  |      0           |        1.40244e+10 |        1        |
| disk_ud                  | ols_nn       |           1.20536  |      0           |        1.40244e+10 |        1        |
| disk_ud                  | wls          |           1.82815  |      0           |        1.43641e+10 |        1        |
| disk_ud                  | mint         |           2.09655  |      0           |        1.53953e+10 |        1        |
| disk_ud                  | bottom_up    |           3.39296  |      0           |        1.51871e+10 |        1        |
| disk_ud                  | bottom_up_nn |           3.39296  |      0           |        1.51871e+10 |        1        |
| memory_um                | wls          |           0.95131  |      0           |        5.88668e+08 |        1        |
| memory_um                | mint         |           0.951478 |      0           |        5.87486e+08 |        1        |
| memory_um                | bottom_up    |           0.961812 |      0           |        5.91004e+08 |        1        |
| memory_um                | bottom_up_nn |           0.961812 |      0           |        5.91004e+08 |        1        |
| memory_um                | ols          |           0.984239 |      0           |        5.92599e+08 |        1        |
| memory_um                | ols_nn       |           0.984239 |      0           |        5.92599e+08 |        1        |
| memory_um                | independent  |           1        |      5.18902e+08 |        5.91004e+08 |        0.333333 |
| memory_um                | top_down     |           1        |      5.89e-06    |        5.92885e+08 |        1        |

eligible_for_final_claims: false