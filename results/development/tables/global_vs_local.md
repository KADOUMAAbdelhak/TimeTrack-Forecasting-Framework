# Global vs local (in-distribution, development)

| family   | method          | base_model   |   mae_rel_mean |   mae_vs_local_mean |
|:---------|:----------------|:-------------|---------------:|--------------------:|
| CU       | global_residual | ridge        |    0.999998    |        -1.48089e-07 |
| CU       | local           | ridge        |    1           |         0           |
| CU       | global_embed    | ridge        |    1.12931     |         0.182089    |
| CU       | global_onehot   | ridge        |    1.16417     |         0.137611    |
| CU       | global_pooled   | ridge        |    1.20501     |         0.267102    |
| UM       | local           | ridge        |    1           |         0           |
| UM       | global_residual | ridge        |    1           |         4.17776e-07 |
| UM       | global_onehot   | ridge        |    3.47112     |         2.04286e+08 |
| UM       | global_pooled   | ridge        |    4.46438     |         3.92012e+08 |
| UM       | global_embed    | ridge        |    8.95513e+07 |         1.97467e+16 |

eligible_for_final_claims: false