# Stage 6A previous-manuscript literature reuse audit

Audit date: 16 October 2026. Internal development artifact, not manuscript prose.

**STAGE_6A_PASS**: all 38 legacy citation keys mapped; ten missing references independently verified and added; original 26 entries preserved; updated 36-entry bibliography compiles. Optional candidates that were not selected do not prevent completion of this reuse audit. **Stage 6 final novelty clearance remains blocked and separate.** No legacy summary clears the missing Ullah/JSS/MMRP methods. No unresolved bibliographic conflict was imported into the accepted additions; known legacy errors are exposed below, not silently retained.

Scope: old_fgcs_rejected/fgcs is a discovery source, not evidence for current scientific claims. Current title and British-English lock are unchanged.

## 1. Previous manuscript sections inspected

Read manuscript.tex, lines 1–1402: front matter/abstract; Introduction (125–287); Related Work (290–494: profiling, cloud forecasting, hierarchical reconciliation and old gap); dataset/hierarchies (497–612); methodology (615–779); experimental protocol (782–916); Results (919–1142); Discussion (1146–1283); Conclusion (1286 onward); availability and end matter. Results/conclusions were inspected to identify material to quarantine, not to reuse findings.

Read the related-work comparison and baseline/protocol tables, and scanned all eight input tables for citations. The old table's unsupported absence marks are not evidence for current comparisons. No old figures, numerical artifacts or experiments were regenerated.

## 2. Total old citation keys

**38 distinct keys** in the main manuscript; all resolve to entries in the old bibliography. No unresolved keys.

## 3. Total old bibliography entries

**38 entries**, all actually cited; zero uncited entries. These are legacy records, not 38 newly verified authoritative sources.

## 4. Citations actually used: complete 38-work ledger

There are **98 individual key occurrences in manuscript.tex** and **6 in the included related-work table**, total **104**. These are key occurrences, not citation-command counts. A comma-separated citation contributes one occurrence per key. Comments are excluded. No extra keys arise in the other seven included tables.

The original metadata below is explicitly **untrusted discovery metadata**. Accepted corrected publication records are in Section 6. An old DOI's presence does not itself verify the old authors, year or title. Each work has exactly one required classification.

### L01. meliani2025timetrack — KEEP_HIGH_PRIORITY

Old title: TimeTrack: A Dataset for Exploring Temporal Patterns and Predictive Insights into OpenAirInterface (OAI) CI/CD Cluster.

Old authors: Abd Elghani Meliani; Sagar Arora; Adlen Ksentini; Raymond Knopp. Old year: 2025. Old venue: IEEE International Conference on Communications (ICC). Old identifier: 10.1109/ICC52391.2025.11161298.

Old use locations: manuscript.tex:186; manuscript.tex:392; manuscript.tex:505; manuscript.tex:509; manuscript.tex:537; manuscript.tex:577; manuscript.tex:1258; manuscript.tex:1358.

Disposition/relevance: Dataset provenance and published cross-resource association; new citation Meliani2025TimeTrack. Do not import the old retained segment, hierarchy, outcomes, or nominal cadence as our measured cadence.

Intended future section(s): Introduction; Methodology; Threats to Validity.

### L02. meliani2026zerotouch — POSSIBLY_USEFUL

Old title: Zero Touch Predictive Orchestration: Automating Time-Series Models for the Cloud-Edge Continuum.

Old authors: Abd Elghani Meliani; Sagar Arora; Adlen Ksentini; Raymond Knopp. Old year: 2026. Old venue: arXiv preprint. Old identifier: 10.48550/arXiv.2606.09787.

Old use locations: manuscript.tex:195; manuscript.tex:396; manuscript.tex:1240; tables/related_work_comparison.tex:20.

Disposition/relevance: PREPRINT_ONLY as verified on arXiv; NAS/data mixing for cold-start nodes. Different sharing axis from resources, not a final journal version of the dataset paper. Not added.

Intended future section(s): Related Work; Discussion.

### L03. meliani2025timetrackkaggle — METADATA_REQUIRES_VERIFICATION

Old title: Open Air Interface CI/CD Timeseries Dataset (TimeTrack).

Old authors: Abd Elghani Meliani. Old year: 2025. Old venue: Kaggle Dataset. Old identifier: https://www.kaggle.com/datasets/abdelghanimeliani/open-air-interface-cicd-timeseries-dataset.

Old use locations: manuscript.tex:186; manuscript.tex:392; manuscript.tex:512; manuscript.tex:1258; manuscript.tex:1354.

Disposition/relevance: Dataset landing page is real, but old title differs from current title and the old year 2025 differs from 2024 in the ICC reference. Current version/date not established; do not invent a dataset citation or reuse old access date. Dataset paper supplies attribution; URL remains discovery/provenance.

Intended future section(s): Methodology.

### L04. hyndman2011optimal — OUT_OF_SCOPE_CURRENT_PAPER

Old title: Optimal combination forecasts for hierarchical time series.

Old authors: Rob J. Hyndman; Roman A. Ahmed; George Athanasopoulos; Han Lin Shang. Old year: 2011. Old venue: Computational Statistics & Data Analysis. Old identifier: 10.1016/j.csda.2011.03.006.

Old use locations: manuscript.tex:154; manuscript.tex:407; manuscript.tex:417; manuscript.tex:707; manuscript.tex:1162; tables/related_work_comparison.tex:15.

Disposition/relevance: Exact hierarchical forecast combination; no independent need in the current resource-task study.

Intended future section(s): None.

### L05. wickramasuriya2019mint — OUT_OF_SCOPE_CURRENT_PAPER

Old title: Optimal Forecast Reconciliation for Hierarchical and Grouped Time Series Through Trace Minimization.

Old authors: Shanika L. Wickramasuriya; George Athanasopoulos; Rob J. Hyndman. Old year: 2019. Old venue: Journal of the American Statistical Association. Old identifier: 10.1080/01621459.2018.1448825.

Old use locations: manuscript.tex:209; manuscript.tex:431; manuscript.tex:734; manuscript.tex:740; manuscript.tex:1162; tables/related_work_comparison.tex:16.

Disposition/relevance: MinT and reconciliation superiority/assumptions are outside the current question.

Intended future section(s): None.

### L06. panagiotelis2021geometric — OUT_OF_SCOPE_CURRENT_PAPER

Old title: Forecast reconciliation: A geometric view with new insights on bias correction.

Old authors: Anastasios Panagiotelis; George Athanasopoulos; Puwasala Gamakumara; Rob J. Hyndman. Old year: 2021. Old venue: International Journal of Forecasting. Old identifier: 10.1016/j.ijforecast.2020.06.004.

Old use locations: manuscript.tex:434.

Disposition/relevance: Projection/coherence geometry is not resource-representation sharing.

Intended future section(s): None.

### L07. athanasopoulos2024hierarchical — OUT_OF_SCOPE_CURRENT_PAPER

Old title: Forecast reconciliation: A review.

Old authors: George Athanasopoulos; Rob J. Hyndman; Nikolaos Kourentzes; Anastasios Panagiotelis. Old year: 2024. Old venue: International Journal of Forecasting. Old identifier: 10.1016/j.ijforecast.2023.10.010.

Old use locations: manuscript.tex:154; manuscript.tex:209; manuscript.tex:417; manuscript.tex:440; manuscript.tex:476; manuscript.tex:707; manuscript.tex:1162; manuscript.tex:1223.

Disposition/relevance: Hierarchy/reconciliation review; not a general MTL source.

Intended future section(s): None.

### L08. zeng2023dlinear — DUPLICATE_CURRENT_LIBRARY

Old title: Are Transformers Effective for Time Series Forecasting?.

Old authors: Ailing Zeng; Muxi Chen; Lei Zhang; Qiang Xu. Old year: 2023. Old venue: Proceedings of the AAAI Conference on Artificial Intelligence. Old identifier: 10.1609/aaai.v37i9.26317.

Old use locations: manuscript.tex:226; manuscript.tex:364; manuscript.tex:368; manuscript.tex:689; manuscript.tex:1155.

Disposition/relevance: Exact DOI/title duplicate of Zeng2023LinearForecasting. Preserve current entry; no second reference.

Intended future section(s): Related Work.

### L09. ke2017lightgbm — OUT_OF_SCOPE_CURRENT_PAPER

Old title: LightGBM: A Highly Efficient Gradient Boosting Decision Tree.

Old authors: Guolin Ke; Qi Meng; Thomas Finley; Taifeng Wang; Wei Chen; Weidong Ma; Qiwei Ye; Tie-Yan Liu. Old year: 2017. Old venue: Advances in Neural Information Processing Systems. Old identifier: none supplied.

Old use locations: manuscript.tex:224; manuscript.tex:348; manuscript.tex:683; manuscript.tex:1155.

Disposition/relevance: Old learned baseline is not evaluated in the locked JSS study; no architecture-survey expansion.

Intended future section(s): None.

### L10. schafer2005shrinkage — OUT_OF_SCOPE_CURRENT_PAPER

Old title: A Shrinkage Approach to Large-Scale Covariance Matrix Estimation and Implications for Functional Genomics.

Old authors: Juliane Sch\"afer; Korbinian Strimmer. Old year: 2005. Old venue: Statistical Applications in Genetics and Molecular Biology. Old identifier: 10.2202/1544-6115.1175.

Old use locations: manuscript.tex:431; manuscript.tex:740.

Disposition/relevance: Old covariance shrinkage was for MinT; no current estimator needs this citation.

Intended future section(s): None.

### L11. harmony2024 — POSSIBLY_USEFUL

Old title: Adaptive Two-Stage Cloud Resource Scaling via Hierarchical Multi-Indicator Forecasting and Bayesian Decision-Making.

Old authors: Yang Luo; Shiyu Wang; Zhemeng Yu; Wei Lu; Xiaofeng Gao; Lintao Ma; Guihai Chen. Old year: 2024. Old venue: arXiv preprint. Old identifier: 10.48550/arXiv.2408.01000.

Old use locations: manuscript.tex:212; manuscript.tex:450; manuscript.tex:476; tables/related_work_comparison.tex:17.

Disposition/relevance: PREPRINT_ONLY. Primary arXiv methods independently verify multi-indicator forecasting and attention ablations; not merely a summing-hierarchy paper. Important constraint, but not added to the compact published-source library; do not claim first inter-indicator sharing. See focused audit.

Intended future section(s): Related Work; Discussion.

### L12. wang2025frt — OUT_OF_SCOPE_CURRENT_PAPER

Old title: FRT: Flow-based Reconcile Transformer for Hierarchical Time Series.

Old authors: Shiyu Wang; Wei Lu; Jiawei Li; Xiaoming Shi; Xinyue Zhong; Zhou Ye; Ming Jin; Qingsong Wen. Old year: 2025. Old venue: Proceedings of the 31st ACM SIGKDD Conference on Knowledge Discovery and Data Mining V.2 (KDD '25). Old identifier: 10.1145/3711896.3737224.

Old use locations: manuscript.tex:456; manuscript.tex:476; tables/related_work_comparison.tex:18.

Disposition/relevance: Flow-based hierarchical reconciliation; not retained solely for mention of data-centre workloads.

Intended future section(s): None.

### L13. gao2026mamiclif — KEEP_HIGH_PRIORITY

Old title: Macro-Micro Collaborative Learning for Logical Data Center Microservice Indicators Forecasting.

Old authors: Mohan Gao; Zhemeng Yu; Yang Luo; Lintao Ma; Yinbo Sun; Yuchen Fang; Xiaofeng Gao. Old year: 2026. Old venue: Proceedings of the ACM Web Conference 2026 (WWW '26). Old identifier: 10.1145/3774904.3792125.

Old use locations: manuscript.tex:461; tables/related_work_comparison.tex:19.

Disposition/relevance: Published microservice-indicator forecasting paper, bibliographically reverified; add Gao2026MaMiClif. Detailed graph/causal and ablation assertions remain method-unverified, not imported from the old summary.

Intended future section(s): Related Work; Discussion.

### L14. ashouri2022fast — OUT_OF_SCOPE_CURRENT_PAPER

Old title: Fast Forecast Reconciliation Using Linear Models.

Old authors: Mahsa Ashouri; Rob J. Hyndman; Galit Shmueli. Old year: 2022. Old venue: Journal of Computational and Graphical Statistics. Old identifier: 10.1080/10618600.2021.1939038.

Old use locations: manuscript.tex:437.

Disposition/relevance: Linear forecast reconciliation is not an estimator used in the present study.

Intended future section(s): None.

### L15. panagiotelis2023probabilistic — OUT_OF_SCOPE_CURRENT_PAPER

Old title: Probabilistic forecast reconciliation: Properties, evaluation and score optimisation.

Old authors: Anastasios Panagiotelis; Puwasala Gamakumara; George Athanasopoulos; Rob J. Hyndman. Old year: 2023. Old venue: European Journal of Operational Research. Old identifier: 10.1016/j.ejor.2022.07.040.

Old use locations: manuscript.tex:440.

Disposition/relevance: Probabilistic reconciliation is outside the current point-forecast study.

Intended future section(s): None.

### L16. agullo2025spikes — POSSIBLY_USEFUL

Old title: Enhancing the output of time series forecasting algorithms for cloud resource provisioning.

Old authors: Ferran Agulló; Alberto Gutierrez-Torre; Jordi Torres; Josep Ll. Berral. Old year: 2025. Old venue: Future Generation Computer Systems. Old identifier: 10.1016/j.future.2025.107833.

Old use locations: manuscript.tex:385; manuscript.tex:479.

Disposition/relevance: Potential accuracy-versus-provisioning discussion, but spike post-processing is not evaluated here. Not added; no fresh full bibliographic clearance claimed after metadata rate limiting.

Intended future section(s): Discussion.

### L17. sus2024signature — POSSIBLY_USEFUL

Old title: Signature-based Adaptive Cloud Resource Usage Prediction Using Machine Learning and Anomaly Detection.

Old authors: Wiktor Sus; Piotr Nawrocki. Old year: 2024. Old venue: Journal of Grid Computing. Old identifier: 10.1007/s10723-024-09764-4.

Old use locations: manuscript.tex:382; manuscript.tex:479.

Disposition/relevance: Verified metadata, anomaly-aware signature prediction is adjacent; present study is not an anomaly detector. Not needed alongside selected provisioning references.

Intended future section(s): Related Work; Discussion.

### L18. masdari2020workload — POSSIBLY_USEFUL

Old title: A survey and classification of the workload forecasting methods in cloud computing.

Old authors: Mohammad Masdari; Afsane Khoshnevis. Old year: 2020. Old venue: Cluster Computing. Old identifier: 10.1007/s10586-019-03010-3.

Old use locations: manuscript.tex:158; manuscript.tex:344; manuscript.tex:476; manuscript.tex:1221.

Disposition/relevance: Verified workload-survey metadata; broader catalogue than needed. Existing direct studies already cover resource forecasting; not added.

Intended future section(s): Related Work.

### L19. khan2022workload — POSSIBLY_USEFUL

Old title: Machine learning (ML)-centric resource management in cloud computing: A review and future directions.

Old authors: Tania Khan; Wenhong Tian; Gang Zhou; Shashikant Ilager; Mingming Gong; Rajkumar Buyya. Old year: 2022. Old venue: Journal of Network and Computer Applications. Old identifier: 10.1016/j.jnca.2022.103405.

Old use locations: manuscript.tex:158; manuscript.tex:351.

Disposition/relevance: Relevant broad management review, but old author metadata wrong. Fresh record identifies Tahseen Khan and Guangyao Zhou, not Tania/Gang. Not added; primary provisioning work preferred.

Intended future section(s): Introduction; Related Work.

### L20. duc2020survey — POSSIBLY_USEFUL

Old title: Machine Learning Methods for Reliable Resource Provisioning in Edge-Cloud Computing: A Survey.

Old authors: Thang Le Duc; Rafael García Leiva; Paolo Casari; Per-Olov Östberg. Old year: 2020. Old venue: ACM Computing Surveys. Old identifier: 10.1145/3341145.

Old use locations: manuscript.tex:297; manuscript.tex:312.

Disposition/relevance: Verified survey identity; edge provisioning is adjacent, not an extra required survey. Not added.

Intended future section(s): Introduction; Related Work.

### L21. calheiros2015workload — KEEP_BACKGROUND

Old title: Workload Prediction Using ARIMA Model and Its Impact on Cloud Applications' QoS.

Old authors: Rodrigo N. Calheiros; Enayat Masoumi; Rajiv Ranjan; Rajkumar Buyya. Old year: 2015. Old venue: IEEE Transactions on Cloud Computing. Old identifier: 10.1109/TCC.2014.2350475.

Old use locations: manuscript.tex:158; manuscript.tex:334.

Disposition/relevance: Add Calheiros2015ARIMA for proactive provisioning and the distinction between request forecasting and downstream QoS. Does not certify operational benefit for our forecasters.

Intended future section(s): Introduction; Discussion.

### L22. islam2012empirical — KEEP_BACKGROUND

Old title: Empirical prediction models for adaptive resource provisioning in the cloud.

Old authors: Sadeka Islam; Jacky Keung; Kevin Lee; Anna Liu. Old year: 2012. Old venue: Future Generation Computer Systems. Old identifier: 10.1016/j.future.2011.05.027.

Old use locations: manuscript.tex:334.

Disposition/relevance: Add Islam2012Provisioning for empirical prediction-based allocation and instance-startup delay motivation. Not treated as a matched four-resource sharing experiment.

Intended future section(s): Introduction; Related Work.

### L23. lorido2014review — OBSOLETE_OR_SUPERSEDED

Old title: A Review of Auto-scaling Techniques for Elastic Applications in Cloud Environments.

Old authors: Tania Lorido-Botran; Jose Miguel-Alonso; Jose A. Lozano. Old year: 2014. Old venue: Journal of Grid Computing. Old identifier: 10.1007/s10723-014-9314-7.

Old use locations: manuscript.tex:136; manuscript.tex:344; manuscript.tex:378.

Disposition/relevance: Superseded for this library selection by broader Qu taxonomy and current empirical sources, not declared scientifically invalid or an earlier version of Qu.

Intended future section(s): Related Work.

### L24. qu2018auto — KEEP_BACKGROUND

Old title: Auto-Scaling Web Applications in Clouds: A Taxonomy and Survey.

Old authors: Chenhao Qu; Rodrigo N. Calheiros; Rajkumar Buyya. Old year: 2018. Old venue: ACM Computing Surveys. Old identifier: 10.1145/3148149.

Old use locations: manuscript.tex:136; manuscript.tex:351; manuscript.tex:378.

Disposition/relevance: Add Qu2018Autoscaling as the single focused autoscaling taxonomy. Author PDF and ACM publication history support 2018; distinguish issue-cover year 2019.

Intended future section(s): Introduction; Related Work; Discussion.

### L25. wen2023transformers — OBSOLETE_OR_SUPERSEDED

Old title: Transformers in Time Series: A Survey.

Old authors: Qingsong Wen; Tian Zhou; Chaoli Zhang; Weiqi Chen; Ziqing Ma; Junchi Yan; Liang Sun. Old year: 2023. Old venue: Proceedings of the Thirty-Second International Joint Conference on Artificial Intelligence (IJCAI). Old identifier: 10.24963/ijcai.2023/759.

Old use locations: manuscript.tex:361.

Disposition/relevance: Generic Transformer survey unnecessary; current original PatchTST/iTransformer/DLinear sources are more specific. Selection-level replacement, not a journal extension.

Intended future section(s): Related Work.

### L26. lim2021temporal — OBSOLETE_OR_SUPERSEDED

Old title: Time-series forecasting with deep learning: a survey.

Old authors: Bryan Lim; Stefan Zohren. Old year: 2021. Old venue: Philosophical Transactions of the Royal Society A. Old identifier: 10.1098/rsta.2020.0209.

Old use locations: manuscript.tex:361.

Disposition/relevance: Generic deep-forecasting survey not needed given existing original architecture sources; not a duplicate of the 2021 Temporal Fusion Transformers paper.

Intended future section(s): Related Work.

### L27. hyndman2006accuracy — KEEP_HIGH_PRIORITY

Old title: Another look at measures of forecast accuracy.

Old authors: Rob J. Hyndman; Anne B. Koehler. Old year: 2006. Old venue: International Journal of Forecasting. Old identifier: 10.1016/j.ijforecast.2006.03.001.

Old use locations: manuscript.tex:758.

Disposition/relevance: Add Hyndman2006Accuracy for error-measure scope/degeneracies. Do not introduce old MASE or mistake current training-IQR NMAE/persistence skill for MASE.

Intended future section(s): Methodology; Discussion.

### L28. bergmeir2018note — KEEP_HIGH_PRIORITY

Old title: A note on the validity of cross-validation for evaluating autoregressive time series prediction.

Old authors: Christoph Bergmeir; Rob J. Hyndman; Bonsoo Koo. Old year: 2018. Old venue: Computational Statistics & Data Analysis. Old identifier: 10.1016/j.csda.2017.11.003.

Old use locations: manuscript.tex:796.

Disposition/relevance: Add Bergmeir2018CrossValidation for conditional CV validity and protocol assumptions, not a blanket statement that all shuffled CV is invalid.

Intended future section(s): Methodology; Threats to Validity.

### L29. makridakis2018statistical — POSSIBLY_USEFUL

Old title: Statistical and Machine Learning forecasting methods: Concerns and ways forward.

Old authors: Spyros Makridakis; Evangelos Spiliotis; Vassilios Assimakopoulos. Old year: 2018. Old venue: PLOS ONE. Old identifier: 10.1371/journal.pone.0194889.

Old use locations: manuscript.tex:364.

Disposition/relevance: Broad comparative caution already represented by DLinear and direct forecasting literature; cannot imply universal failure of ML. Not added.

Intended future section(s): Related Work; Discussion.

### L30. shi2016edge — OUT_OF_SCOPE_CURRENT_PAPER

Old title: Edge Computing: Vision and Challenges.

Old authors: Weisong Shi; Jie Cao; Quan Zhang; Youhuizi Li; Lanyu Xu. Old year: 2016. Old venue: IEEE Internet of Things Journal. Old identifier: 10.1109/JIOT.2016.2579198.

Old use locations: manuscript.tex:131.

Disposition/relevance: General edge vision is not needed to position this fixed cloud/runtime experiment.

Intended future section(s): None.

### L31. satyanarayanan2017emergence — OUT_OF_SCOPE_CURRENT_PAPER

Old title: The Emergence of Edge Computing.

Old authors: Mahadev Satyanarayanan. Old year: 2017. Old venue: Computer. Old identifier: 10.1109/MC.2017.9.

Old use locations: manuscript.tex:131.

Disposition/relevance: General edge-computing origin/background is too remote from the controlled sharing question.

Intended future section(s): None.

### L32. buyya2019manifesto — METADATA_REQUIRES_VERIFICATION

Old title: A Manifesto for Future Generation Cloud Computing: Research Directions for the Next Decade.

Old authors: Rajkumar Buyya; Satish Narayana Srirama; Giuliano Casale; Rodrigo Calheiros; Yogesh Simmhan; Blesson Varghese; Erol Gelenbe; Bahman Javadi; Luis Miguel Vaquero; Marco A. S. Netto; Adel Nadjaran Toosi; Maria Alejandra Rodriguez; Ignacio M. Llorente; Stefano De Pellegrini; Giuseppe Di Modica; Eyal De Lara; Omer Rana; Wanlei Zhou; Hai Jin; Anastasios V. Gkoutos; Yike Shen; Yiran Wang. Old year: 2019. Old venue: ACM Computing Surveys. Old identifier: 10.1145/3241737.

Old use locations: manuscript.tex:131; manuscript.tex:297.

Disposition/relevance: Broad future-cloud motivation is weak for this purpose and the legacy ordered author list is substantially corrupted. Do not reuse that entry. Publisher-deposited author data expose discrepancies; rewrite/reverify if ever needed.

Intended future section(s): Introduction.

### L33. taherizadeh2018monitoring — KEEP_HIGH_PRIORITY

Old title: Monitoring self-adaptive applications within edge computing frameworks: A state-of-the-art review.

Old authors: Salman Taherizadeh; Andrew C. Jones; Ian Taylor; Zhiming Zhao; Vlado Stankovski. Old year: 2018. Old venue: Journal of Systems and Software. Old identifier: 10.1016/j.jss.2017.10.033.

Old use locations: manuscript.tex:297; manuscript.tex:312.

Disposition/relevance: Add Taherizadeh2018Monitoring for JSS monitoring requirements and self-adaptive applications; not a forecasting-effectiveness experiment.

Intended future section(s): Introduction; Related Work; Discussion.

### L34. toka2021kubernetes — KEEP_BACKGROUND

Old title: Machine Learning-Based Scaling Management for Kubernetes Edge Clusters.

Old authors: László Toka; Gergely Dobreff; Balázs Fodor; Balázs Sonkoly. Old year: 2021. Old venue: IEEE Transactions on Network and Service Management. Old identifier: 10.1109/TNSM.2021.3052837.

Old use locations: manuscript.tex:161; manuscript.tex:304; manuscript.tex:351; manuscript.tex:375.

Disposition/relevance: Add Toka2021KubernetesScaling for software management using competing forecast methods. Forecast/controller scope differs from our no-live-controller study.

Intended future section(s): Introduction; Related Work; Discussion.

### L35. rossi2020geo — OUT_OF_SCOPE_CURRENT_PAPER

Old title: Geo-distributed efficient deployment of containers with Kubernetes.

Old authors: Fabiana Rossi; Valeria Cardellini; Francesco Lo Presti; Matteo Nardelli. Old year: 2020. Old venue: Computer Communications. Old identifier: 10.1016/j.comcom.2020.04.061.

Old use locations: manuscript.tex:304; manuscript.tex:375.

Disposition/relevance: Container placement/deployment, not the required forecasting contrast; old surname Presti must be Lo Presti if reused.

Intended future section(s): None.

### L36. casalicchio2019container — OUT_OF_SCOPE_CURRENT_PAPER

Old title: Container Orchestration: A Survey.

Old authors: Emiliano Casalicchio. Old year: 2019. Old venue: Systems Modeling: Methodologies and Tools. Old identifier: 10.1007/978-3-319-92378-9_14.

Old use locations: manuscript.tex:161; manuscript.tex:304; manuscript.tex:375.

Disposition/relevance: Orchestration catalogue does not add a necessary forecasting or sharing source.

Intended future section(s): None.

### L37. holm1979simple — OUT_OF_SCOPE_CURRENT_PAPER

Old title: A Simple Sequentially Rejective Multiple Test Procedure.

Old authors: Sture Holm. Old year: 1979. Old venue: Scandinavian Journal of Statistics. Old identifier: none supplied.

Old use locations: manuscript.tex:881.

Disposition/relevance: Current protocol does not implement the old Holm test families. Do not import old inferential design.

Intended future section(s): None.

### L38. hyndman2021forecasting — KEEP_BACKGROUND

Old title: Forecasting: Principles and Practice.

Old authors: Rob J. Hyndman; George Athanasopoulos. Old year: 2021. Old venue: OTexts. Old identifier: https://otexts.com/fpp3/.

Old use locations: manuscript.tex:407; manuscript.tex:1221.

Disposition/relevance: Add Hyndman2021Forecasting for naive baselines and future-only time-series evaluation. Use non-hierarchical toolbox sections; no chapter 11 reconciliation transfer.

Intended future section(s): Methodology; Threats to Validity.

## 5. Comparison with the original current library

One exact duplicate by normalised DOI and title: old `zeng2023dlinear` maps to current `Zeng2023LinearForecasting` (10.1609/aaai.v37i9.26317). Different BibTeX entry type/key is not a different scientific work. No duplicate was added.

No equivalent conference/journal pair among the selected additions was found in the original 26. Shared authors or acronyms do not make separate papers versions of one another. The ICC dataset paper and Zero Touch preprint have different purposes; neither is an extension of the other's controlled experiment. The old Lim/Zohren survey is not the Temporal Fusion Transformers paper considered at Stage 6. Gao/MaMiClif and Gao/OMCR have different authors, papers and DOIs.

Related but not exact redundancy: current direct forecasting/MTL papers replace the need for several broad surveys; Qu supplies the focused autoscaling taxonomy instead of also adding Lorido-Botran; current original architecture sources obviate a generic deep-learning/Transformer survey. “OBSOLETE_OR_SUPERSEDED” below is a library-selection decision, not a finding that a valid source became false or an exact later version exists.

## 6. Reusable missing references: independently verified accepted records

Ten additions, each with a distinct role. All original 26 records remain unchanged. Metadata verification is separate from full protocol/novelty verification. Volume/issue apply to journal entries; none is invented for standalone proceedings or the textbook.

### Meliani2025TimeTrack (recovered from meliani2025timetrack)

**TimeTrack: A Dataset for Exploring Temporal Patterns and Predictive Insights into OpenAirInterface (OAI) CI/CD Cluster**

Ordered authors: Abd Elghani Meliani; Sagar Arora; Adlen Ksentini; Raymond Knopp.

Verified publication: 2025; ICC 2025 - IEEE International Conference on Communications; pp. 1978–1983; DOI 10.1109/ICC52391.2025.11161298.

Authorities: [primary record](https://www.eurecom.fr/publication/8076); [author/institution/publisher evidence](https://www.eurecom.fr/publication/8076/download/comsys-publi-8076.pdf). Fresh [publisher-deposited Crossref record](https://api.crossref.org/works/10.1109%2FICC52391.2025.11161298).

Verification/content depth: Institutional record, six-page author-deposited paper and fresh IEEE/Crossref record. Published ICC 2025 paper. Pages newly completed as 1978–1983. Crossref missegments the first two author names; institutional author identities and the paper establish the normal surname order retained here.

Future use: Introduction; Methodology; Threats to Validity. Dataset provenance and published cross-resource association; new citation Meliani2025TimeTrack. Do not import the old retained segment, hierarchy, outcomes, or nominal cadence as our measured cadence.

### Gao2026MaMiClif (recovered from gao2026mamiclif)

**Macro-Micro Collaborative Learning for Logical Data Center Microservice Indicators Forecasting**

Ordered authors: Mohan Gao; Zhemeng Yu; Yang Luo; Lintao Ma; Yinbo Sun; Yuchen Fang; Xiaofeng Gao.

Verified publication: 2026; Proceedings of the ACM Web Conference 2026; pp. 5010–5020; DOI 10.1145/3774904.3792125.

Authorities: [primary record](https://www2026.thewebconf.org/accepted/research-tracks.html); [author/institution/publisher evidence](https://doi.org/10.1145/3774904.3792125). Fresh [publisher-deposited Crossref record](https://api.crossref.org/works/10.1145%2F3774904.3792125).

Verification/content depth: Official accepted research-track list, publisher-deposited Crossref record and DBLP confirm seven ordered authors, title, proceedings, 2026 and 5010–5020. Published peer-reviewed proceedings. ACM full text returned 403; bibliographic acceptance does not certify graph/causal mechanisms or absence of an S2-equivalent arm.

Future use: Related Work; Discussion. Published microservice-indicator forecasting paper, bibliographically reverified; add Gao2026MaMiClif. Detailed graph/causal and ablation assertions remain method-unverified, not imported from the old summary.

### Taherizadeh2018Monitoring (recovered from taherizadeh2018monitoring)

**Monitoring self-adaptive applications within edge computing frameworks: A state-of-the-art review**

Ordered authors: Salman Taherizadeh; Andrew C. Jones; Ian Taylor; Zhiming Zhao; Vlado Stankovski.

Verified publication: 2018; Journal of Systems and Software; volume 136; pp. 19–38; DOI 10.1016/j.jss.2017.10.033.

Authorities: [primary record](https://www.sciencedirect.com/science/article/pii/S016412121730256X); [author/institution/publisher evidence](https://dare.uva.nl/id/2730c9ff-29df-499e-8cae-d9cf83529aaf). Fresh [publisher-deposited Crossref record](https://api.crossref.org/works/10.1016%2Fj.jss.2017.10.033).

Verification/content depth: Publisher abstract/highlights, institutional record and fresh Crossref agree. Published JSS review, not empirical forecasting evidence.

Future use: Introduction; Related Work; Discussion. Add Taherizadeh2018Monitoring for JSS monitoring requirements and self-adaptive applications; not a forecasting-effectiveness experiment.

### Toka2021KubernetesScaling (recovered from toka2021kubernetes)

**Machine Learning-Based Scaling Management for Kubernetes Edge Clusters**

Ordered authors: László Toka; Gergely Dobreff; Balázs Fodor; Balázs Sonkoly.

Verified publication: 2021; IEEE Transactions on Network and Service Management; volume 18; issue 1; pp. 958–972; DOI 10.1109/TNSM.2021.3052837.

Authorities: [primary record](https://ieeexplore.ieee.org/document/9328525/); [author/institution/publisher evidence](https://netsoft.gsuite.tmit.bme.hu/publications). Fresh [publisher-deposited Crossref record](https://api.crossref.org/works/10.1109%2FTNSM.2021.3052837).

Verification/content depth: IEEE/Crossref and author-group publications/research descriptions verify identity and scaling-management role. Published journal article. Full experimental protocol not inspected; no claim of equivalent or absent sharing controls.

Future use: Introduction; Related Work; Discussion. Add Toka2021KubernetesScaling for software management using competing forecast methods. Forecast/controller scope differs from our no-live-controller study.

### Qu2018Autoscaling (recovered from qu2018auto)

**Auto-Scaling Web Applications in Clouds: A Taxonomy and Survey**

Ordered authors: Chenhao Qu; Rodrigo N. Calheiros; Rajkumar Buyya.

Verified publication: 2018; ACM Computing Surveys; volume 51; issue 4; article 73, pp. 73:1–73:33; DOI 10.1145/3148149.

Authorities: [primary record](https://doi.org/10.1145/3148149); [author/institution/publisher evidence](https://clouds.cis.unimelb.edu.au/papers/AutoScaleWebAppClouds-ACMCS.pdf). Fresh [publisher-deposited Crossref record](https://api.crossref.org/works/10.1145%2F3148149).

Verification/content depth: ACM article publication history, author-deposited final paper first pages and DBLP support full title/subtitle, article 73, 33 pages and 2018. Crossref omits subtitle; its print/issue date is 2019, while article publication and paper reference format are July 2018. Use 2018, documenting the distinction rather than silently guessing.

Future use: Introduction; Related Work; Discussion. Add Qu2018Autoscaling as the single focused autoscaling taxonomy. Author PDF and ACM publication history support 2018; distinguish issue-cover year 2019.

### Calheiros2015ARIMA (recovered from calheiros2015workload)

**Workload Prediction Using ARIMA Model and Its Impact on Cloud Applications' QoS**

Ordered authors: Rodrigo N. Calheiros; Enayat Masoumi; Rajiv Ranjan; Rajkumar Buyya.

Verified publication: 2015; IEEE Transactions on Cloud Computing; volume 3; issue 4; pp. 449–458; DOI 10.1109/TCC.2014.2350475.

Authorities: [primary record](https://doi.org/10.1109/TCC.2014.2350475); [author/institution/publisher evidence](https://clouds.cis.unimelb.edu.au/papers/WorkloadPredictCloud2015.pdf). Fresh [publisher-deposited Crossref record](https://api.crossref.org/works/10.1109%2FTCC.2014.2350475).

Verification/content depth: Fresh IEEE/Crossref metadata plus author-deposited published paper abstract/introduction. Published journal article; request-rate/ARIMA provisioning motivation, not resource-task sharing evidence. 2014 DOI versus final 2015 issue is not an error.

Future use: Introduction; Discussion. Add Calheiros2015ARIMA for proactive provisioning and the distinction between request forecasting and downstream QoS. Does not certify operational benefit for our forecasters.

### Islam2012Provisioning (recovered from islam2012empirical)

**Empirical prediction models for adaptive resource provisioning in the cloud**

Ordered authors: Sadeka Islam; Jacky Keung; Kevin Lee; Anna Liu.

Verified publication: 2012; Future Generation Computer Systems; volume 28; issue 1; pp. 155–162; DOI 10.1016/j.future.2011.05.027.

Authorities: [primary record](https://doi.org/10.1016/j.future.2011.05.027); [author/institution/publisher evidence](https://scholars.cityu.edu.hk/en/publications/empirical-prediction-models-for-adaptive-resource-provisioning-in/). Fresh [publisher-deposited Crossref record](https://api.crossref.org/works/10.1016%2Fj.future.2011.05.027).

Verification/content depth: Publisher-deposited Crossref and author-institution record/abstract agree on authors and final 2012 issue. Peer-reviewed journal article. Provisioning motivation only; exact resource-task design not established from an abstract.

Future use: Introduction; Related Work. Add Islam2012Provisioning for empirical prediction-based allocation and instance-startup delay motivation. Not treated as a matched four-resource sharing experiment.

### Hyndman2006Accuracy (recovered from hyndman2006accuracy)

**Another look at measures of forecast accuracy**

Ordered authors: Rob J. Hyndman; Anne B. Koehler.

Verified publication: 2006; International Journal of Forecasting; volume 22; issue 4; pp. 679–688; DOI 10.1016/j.ijforecast.2006.03.001.

Authorities: [primary record](https://doi.org/10.1016/j.ijforecast.2006.03.001); [author/institution/publisher evidence](https://robjhyndman.com/publications/another-look-at-measures-of-forecast-accuracy/). Fresh [publisher-deposited Crossref record](https://api.crossref.org/works/10.1016%2Fj.ijforecast.2006.03.001).

Verification/content depth: Crossref and author's record/abstract/BibTeX agree on complete metadata. Published journal methodology paper. Supports error-measure interpretation; no metric or frozen analysis changes.

Future use: Methodology; Discussion. Add Hyndman2006Accuracy for error-measure scope/degeneracies. Do not introduce old MASE or mistake current training-IQR NMAE/persistence skill for MASE.

### Bergmeir2018CrossValidation (recovered from bergmeir2018note)

**A note on the validity of cross-validation for evaluating autoregressive time series prediction**

Ordered authors: Christoph Bergmeir; Rob J. Hyndman; Bonsoo Koo.

Verified publication: 2018; Computational Statistics & Data Analysis; volume 120; pp. 70–83; DOI 10.1016/j.csda.2017.11.003.

Authorities: [primary record](https://doi.org/10.1016/j.csda.2017.11.003); [author/institution/publisher evidence](https://robjhyndman.com/publications/cv-time-series/). Fresh [publisher-deposited Crossref record](https://api.crossref.org/works/10.1016%2Fj.csda.2017.11.003).

Verification/content depth: Crossref and author's record/abstract/BibTeX agree. Published journal methodology paper. K-fold CV can be valid for purely autoregressive models with uncorrelated errors; not evidence for an unconditional ban on shuffling.

Future use: Methodology; Threats to Validity. Add Bergmeir2018CrossValidation for conditional CV validity and protocol assumptions, not a blanket statement that all shuffled CV is invalid.

### Hyndman2021Forecasting (recovered from hyndman2021forecasting)

**Forecasting: Principles and Practice**

Ordered authors: Rob J. Hyndman; George Athanasopoulos.

Verified publication: 2021; OTexts; third edition; no assigned DOI verified.

Authorities: [primary record](https://otexts.com/fpp3/); [author/institution/publisher evidence](https://otexts.com/fpp3/toolbox.html). 

Verification/content depth: Publisher's preferred citation confirms authors, 2021, third edition and OTexts Melbourne. Published textbook; no DOI, journal issue or page range applies. Non-hierarchical toolbox sections inspected for naive baselines and rolling-origin evaluation. Online version updated 14 October 2026, accessed 16 October 2026.

Future use: Methodology; Threats to Validity. Add Hyndman2021Forecasting for naive baselines and future-only time-series evaluation. Use non-hierarchical toolbox sections; no chapter 11 reconciliation transfer.

## 7. Rejected and out-of-scope decisions

| Classification | Count | Action |
|---|---:|---|
| KEEP_HIGH_PRIORITY | 5 | Added after independent verification |
| KEEP_BACKGROUND | 5 | Added after independent verification |
| DUPLICATE_CURRENT_LIBRARY | 1 | Reuse existing current key |
| POSSIBLY_USEFUL | 8 | Not added; specific conditional role or redundant coverage |
| METADATA_REQUIRES_VERIFICATION | 2 | Not added; do not trust legacy dataset date/title or manifesto authors |
| OBSOLETE_OR_SUPERSEDED | 3 | Not added; selection covered by preferred sources, not scientifically discredited |
| OUT_OF_SCOPE_CURRENT_PAPER | 14 | Not added |
| REJECT | 0 | No additional blanket scientific rejection |
| **Total** | **38** | **10 additions; 1 already represented; 27 not added** |

For reporting “relevant”, **24** have at least broad contextual/methodological/discovery relevance (38 minus 14 out of scope); this includes weaker and held candidates. Only **11 are retained for current citation use**: ten additions plus DLinear already present. Do not present all 24 as newly accepted or metadata-cleared.

## 8. Obsolete hierarchy/reconciliation material

Do not transfer Hyndman optimal combination, MinT, geometric projection, reconciliation review, covariance shrinkage, fast/probabilistic reconciliation, FRT, or their old comparison table merely because they concern multiple series. A physical summing hierarchy differs from context inputs and shared task parameters. LightGBM is an old baseline, not an evaluated current model.

Discard the old gap about exact machine-to-cluster identities, coherence, bottom-up/WLS/MinT/top-down selectivity, aggregate-versus-bottom costs, hierarchy validation and old RQ1–RQ5. Avoid “coherent forecast”, “bottom/top”, “reconciliation superiority”, “hierarchy-aware accuracy gains” and “conservation” when describing S1/S2/M1.

HARMONY and MaMiClif are not discarded just for hierarchical terminology: their inter-indicator modelling may be relevant independently of exact summing constraints. Their detailed relevance is handled separately, not by reusing the old hierarchy comparison.

## 9. Reusable background concepts: category-by-category audit

All items are conceptual specifications, not sentences for insertion. Reuse means independently rewrite later with verified citations, never copy wording.

| Category | Concept/potential use | Classification and safeguard |
|---|---|---|
| A software/runtime telemetry | Forecasts can inform runtime decisions | REUSABLE_CONCEPT; Taherizadeh/Toka; not proof of our operational effectiveness |
| B cloud-resource forecasting | Resource forecasting is established | REUSABLE_CONCEPT; direct Stage 6 studies, not a novelty claim |
| C workload/resource prediction | Request load and resource demand are distinct prediction targets | REQUIRES_REFRAMING; Calheiros/Islam; do not equate request rate with all resources |
| D CPU forecasting | CPU is an important but incomplete operational signal | REUSABLE_CONCEPT; TimeTrack; no inherited CPU winner |
| E memory forecasting | Memory is a separate monitored resource with workload-dependent behaviour | REQUIRES_REFRAMING; no universal smoothness or old EWMA conclusion |
| F network/throughput | Network throughput, RTT/jitter and request rate differ | REQUIRES_REFRAMING; no transfer of old network-hierarchy exclusion |
| G disk I/O | Used-disk level differs from read/write throughput | REQUIRES_REFRAMING; TimeTrack schema; no reset mechanism or old level result imported |
| H multivariate forecasting | Multiple histories may supply covariates | REUSABLE_CONCEPT; existing Ullah/esDNN etc.; no automatic benefit |
| I cross-resource dependence | Associations motivate a controlled test | REQUIRES_REFRAMING; association is not incremental predictive value or causation |
| J LSTM/RNN | Established sequential forecasting models | REUSABLE_CONCEPT; current Hochreiter/MTL sources already present; no need for generic survey |
| K monitoring/observability | Monitoring requirements inform software adaptation | REUSABLE_CONCEPT; Taherizadeh; do not claim a new observability stack |
| L resource management | Delayed actuation motivates forecasting | REUSABLE_CONCEPT; Islam/Calheiros/Qu; no measured SLA savings here |
| M evaluation | Simple baselines and metric interpretation matter | REUSABLE_CONCEPT; Hyndman/Koehler and FPP3; do not add old metrics |
| N temporal protocol | Selection must reflect intended future prediction and avoid future-label access | REQUIRES_REFRAMING; FPP3/Cerqueira; Bergmeir is conditional, not a blanket CV prohibition |
| O limitations/generalisation | Separate source, resource, model and decision scope | REUSABLE_CONCEPT; current frozen protocol governs actual limits |
| P JSS framing | Information-sharing choices affect runtime forecasting engineering | REQUIRES_REFRAMING; monitoring/performance engineering, not application-profile ontology |
| Hierarchy-only concepts | Exact reconciliation/coherence as the core contribution | NO_LONGER_RELEVANT |
| Claimed causal CPU–network coupling | Old manuscript supplies no verified general relationship | REQUIRES_NEW_CITATION; do not manufacture a relationship |

## 10. Useful JSS/software-engineering framing

Use Taherizadeh for monitoring requirements in self-adaptive applications; Toka for prediction-informed scaling; Calheiros/Islam for the distinction between prediction and resource-provisioning outcomes; Qu for MAPE-loop concerns and costs of over/under-provisioning. These complement current Di Menna/Bauer/Syu, rather than replacing them.

Frame our evaluated contribution as forecast-design evidence for runtime telemetry. Predictive accuracy, controller performance, SLA/SLO compliance, anomaly detection, energy and cost savings are different outcomes. We measured no new live controller, service-quality impact, anomaly anticipation, capacity-planning deployment or profile-system integration in this audit. Avoid the old unsupported universal claim that cloud forecasters all optimise independent streams.

## 11. Useful cross-resource literature and limits

**TimeTrack:** [Primary dataset paper](https://www.eurecom.fr/publication/8076/download/comsys-publi-8076.pdf), Section III-B/Fig. 1, reports CPU–memory and memory–used-disk associations on some machines. It distinguishes disk occupancy from read/write throughput and does not establish a general CPU–network forecasting benefit. Such associations justify asking the S1–S2 question, not its answer. They are contemporaneous observations, not proof of lagged conditional information after target history. Exact correlation numbers, causal workload explanations and forecasting outcomes are not imported. The paper's nominal 45-second interval also does not replace our measured cadence.

**HARMONY:** [Primary preprint](https://arxiv.org/html/2408.01000v1), Sections 2–3 and 5.1/5.3, explicitly consumes request/consumption/quality histories, embeds indicators and uses hierarchical attention. It evaluates four cloud datasets, with attention and flow-component ablations. This is relevant without physical reconciliation and constrains claims to introduce inter-indicator modelling. Its inspected ablations replace hierarchical attention with full attention or remove flow; they are not our fixed-input separate-target S2 bridge. Preprint status is not silently promoted to peer review. Held rather than added; search did not verify a final successor.

**MaMiClif:** [Official research-track list](https://www2026.thewebconf.org/accepted/research-tracks.html) and publisher-deposited record verify the published microservice-indicator study. The old graph/causal-dependency description is discovery context only: primary full methods were unavailable, so no conclusion about its input/shared-representation control follows. Add for literature coverage and prioritise methods inspection before drafting an absence claim.

No general CPU–throughput, CPU–disk-write or benefit from correlation alone was verified from the old manuscript. Existing Stage 6 multivariate papers remain the main forecasting evidence. RTT/jitter association is not CPU/network-throughput association. Disk occupancy is not I/O rate. Correlation-based grouping is not a tested explanation for our results.

## 12. Useful forecasting-methodology literature

- FPP3 toolbox: naive baselines and future-only rolling evaluation; selected outside its hierarchical chapter.
- Hyndman/Koehler: accuracy measures have distinct units/scales and degeneracies. Current training-IQR NMAE, persistence-relative skill and MacroMAE retain their exact definitions. No old MASE denominator is transferred.
- Bergmeir et al.: purely autoregressive models with uncorrelated errors can admit ordinary K-fold CV. The legacy use immediately after “no random shuffling” is not sufficient support for a categorical prohibition. Our prospective purging/segmentation remains a design choice documented by the frozen implementation.
- Current Cerqueira reference already supplies complementary temporal-evaluation evidence. Do not claim that a new citation validates every implementation detail.
- Do not transfer old three expanding folds, L=32, one-step component-0 scoring, moving-block bootstrap with 5,000 replicates, Holm families, peak thresholds, output-width semantics or old seeds as current methodology. No Holm reference is added because the current stated protocol does not use those test families.
- Keep genuine forecast lead separate from joint output width; current multi-horizon resource results cannot be replaced by the old one-step configuration checks.

## 13. Metadata corrections and discrepancies found

1. **TimeTrack:** added missing proceedings pages **1978–1983** and official ICC booktitle. The fresh Crossref name fields segment “Meliani Abd Elghani” as surname Elghani and “Arora Sagar” as surname Sagar. Institutional author identities (MELIANI/ARORA) and the paper support the normal names retained in BibTeX; this is a documented deposit-parsing anomaly, not an invented author.
2. **Qu:** retain 2018 article publication/reference-format year. ACM issue cover/Crossref print date says July 2019. Full title includes subtitle; Crossref's title-only field omits it. Article **73**, pages **73:1–73:33**.
3. **Khan review:** old first author **Tania Khan** is **Tahseen Khan** in the fresh publisher deposit; old **Gang Zhou** is **Guangyao Zhou**. Not transferred.
4. **Buyya manifesto:** old entry contains **22** names whereas fresh publisher-deposited metadata contain **25**, with substantial substitutions/omissions, not just accent variants. For example, the authoritative sequence after Llorente includes Sabrina De Capitani Di Vimercati, Pierangela Samarati, Dejan Milojicic, Carlos Varela, Rami Bahsoon and Marcos Dias De Assuncao. Later names include Wolfgang Gentzsch, Albert Y. Zomaya and Haiying Shen. Do not reuse the old list; not added.
5. **Rossi deployment:** old `Presti, Francesco Lo` should retain compound surname **Lo Presti, Francesco**. Not added.
6. **Kaggle:** current landing title is “TimeTrack: OAI CI/CD cluster TimeSeries dataset”, not the old title. The ICC paper cites a 2024 release; old entry says 2025. Current dataset-version publication date was not independently established; old access date cannot be reused as the current check. Not added.
7. **MaMiClif:** use the official proceedings title without the old hand-expanded conference alias. Publication date is not assumed to equal a rescheduled conference event date.
8. **Masdari / Duc / Casalicchio:** online dates differ from print issue/book dates; do not re-date an entry solely from Crossref's first published field. These unselected records are not silently repaired or imported.
9. **DLinear:** existing current entry already represents the same DOI; a conference-versus-proceedings-journal BibTeX representation is not a separate reference.
10. Added entries preserve protected TimeTrack/OpenAirInterface/OAI/CI/CD, ARIMA, QoS and Kubernetes tokens, author accents and proper compound names. Published titles are not respelled into British English.

Known incorrect unselected records remain unchanged in the archived old bibliography. The audit records them explicitly; no accepted new entry has an unresolved identity conflict.

## 14. References added to current references.bib

- `meliani2025timetrack` → `Meliani2025TimeTrack`
- `gao2026mamiclif` → `Gao2026MaMiClif`
- `taherizadeh2018monitoring` → `Taherizadeh2018Monitoring`
- `toka2021kubernetes` → `Toka2021KubernetesScaling`
- `qu2018auto` → `Qu2018Autoscaling`
- `calheiros2015workload` → `Calheiros2015ARIMA`
- `islam2012empirical` → `Islam2012Provisioning`
- `hyndman2006accuracy` → `Hyndman2006Accuracy`
- `bergmeir2018note` → `Bergmeir2018CrossValidation`
- `hyndman2021forecasting` → `Hyndman2021Forecasting`

## 15. References deliberately not added

The complete ledger identifies all 28 old works without a new addition: one duplicate already in the library, 14 out of scope, eight possible future sources, three selection-superseded surveys and two metadata-held records. This yields **27 unretained works**, plus the retained DLinear duplicate. HARMONY is held as a relevant preprint, not dismissed as irrelevant; Zero Touch is a different data-mixing/AutoML question. Agulló/Sus may become useful if operational-error interpretation becomes central, without inventing peak experiments. The dataset landing page remains an access URL, not a falsely dated release record. No arbitrary final-reference target was imposed.

## 16. Proposed effect on future Introduction

Keep the Stage 6 six-purpose blueprint. Strengthen P1 with monitoring/self-adaptation and provisioning delays (Taherizadeh, Islam, Calheiros, Qu/Toka). Use dataset provenance and association as motivation in P2, not proof of S2 benefit. P3 distinguishes covariate information, target organisation and parameter sharing. P4 retains a qualified experimental question, with HARMONY/MaMiClif constraints acknowledged; no priority clearance. P5–P6 keep current dataset roles and scoped contributions. Do not insert old profile-ontology/coherence narratives, marketing claims or reconciliation outcomes.

## 17. Proposed effect on future Related Work

Retain four subsections:
1. Runtime and cloud-resource forecasting: add TimeTrack provenance as needed, monitoring/management context, and MaMiClif; no independent reconciliation subsection.
2. Information scope and sharing: distinguish contemporaneous association, additional predictive histories, inter-indicator architecture and task-parameter sharing; consider HARMONY cautiously if eventually cited.
3. MTL/task relatedness/adverse transfer: existing foundations and forecasting MTL sources remain; old manuscript contributes no replacement theory.
4. Evaluation gap and scope: strengthened metric and temporal-protocol grounding; do not assert universal absent controls.

No new subsection is justified by the old review. The old hierarchy-centred organisation is not a template.

## 18. Proposed effect on future Discussion

| Observation/evaluated scope | Literature connection | Limit or untested hypothesis |
|---|---|---|
| S2 contextual effects are conditional | TimeTrack associations; existing multivariate forecasting | Correlation does not establish incremental prediction; no causal resource mechanism measured |
| Shared-model outcomes differ from context-only outcomes | Existing MTL/task-relatedness literature; relevant multi-indicator designs | Do not substitute physical hierarchy theory or claim measured gradient conflict |
| Accuracy and efficiency are jointly relevant | Provisioning/scaling literature motivates consequences | No measured SLA, latency, energy or controller-cost improvement follows |
| Source/temporal heterogeneity matters | Current replication scope and temporal-evaluation literature | Old single-segment findings or data-quality rankings do not transfer |
| Error measures and baselines affect interpretation | Hyndman/Koehler, FPP3 and current Cerqueira | No metric definition, aggregation rule or frozen result changed |

No Discussion prose drafted.

## 19. No old prose copied

Confirmed. The audit paraphrases concepts and records bibliographic titles/metadata only. No sentences were copied into manuscript.tex or any manuscript section.

## 20. No old scientific claims imported; Stage 6 gate separate

Confirmed. No old algorithm ranking, reconciliation result, resource winner, causal explanation, numerical finding, hierarchy-validation outcome or novelty claim was imported as current evidence. The old manuscript contains none of the three missing-method papers (Ullah 2023, Di Menna JSS 2026, MMRP 2025). Their Stage 6 UNCLEAR cells remain unchanged. New MaMiClif metadata do not certify its method controls either.

## 21. Updated bibliography technical validation

**36 entries = original 26 unchanged + 10 verified additions.** **28 DOI values, all unique; 36 unique keys; zero missing core field sets; zero unresolved legacy citation keys.** New types are CAS-compatible article/inproceedings/book. Original entry objects were compared field-for-field and order-for-order.

Temporary test directory: `/private/tmp/stage6a-bib-validation.fRXyHw`. Test source uses `\nocite{*}` outside the manuscript, natbib and unchanged cas-model2-names.bst.

Exact sequence executed:

```sh
/Users/fgtek002/Library/TeXLive/2026/bin/universal-darwin/pdflatex -interaction=nonstopmode -halt-on-error validate.tex
/Users/fgtek002/Library/TeXLive/2026/bin/universal-darwin/bibtex validate
/Users/fgtek002/Library/TeXLive/2026/bin/universal-darwin/pdflatex -interaction=nonstopmode -halt-on-error validate.tex
/Users/fgtek002/Library/TeXLive/2026/bin/universal-darwin/pdflatex -interaction=nonstopmode -halt-on-error validate.tex
```

All four exit statuses **0**. pdfTeX 1.40.29/BibTeX 0.99e, TeX Live 2026. Final temporary PDF: **3 pages, 85,169 bytes, 36 bibliography items**. All three pages rendered and visually inspected under the PDF inspection workflow; no clipping/overlap or malformed names/acronyms. No manuscript build or manuscript PDF update was needed.

Warnings: two existing empty-page warnings for ICLR PatchTST and iTransformer (**EXPECTED_METADATA_NOT_APPLICABLE**); three existing underfull hboxes for Fifty/PCGrad (**TYPESETTING_ONLY**, badness 1400/5592/1596). Initial missing .bbl and rerun notices resolved normally. No new missing field warning, fatal error, undefined reference/citation or overfull box. Qu's article pagination, TimeTrack names and pages, author accents and title case reviewed in .bbl/rendering.

Validated references.bib SHA-256: **cbceabcca409cac51dad9b21db2caedb7c20a52c61d64df26bedb0cbd7011b70**.

## 22. Preservation and handoff

Only repository writes for this task: references.bib additions and this audit. Stage 6 novelty_audit.md/reference_verification.md are historical records of the 26-entry audit and were left unchanged; this document supplies the subsequent 36-entry result.

No substantive manuscript.tex changes, no frozen scientific artifact changes, no old manuscript/bibliography changes, no experiments, no commit and no push. Temporary validation/research files are outside the repository. Pre-existing untracked manuscript/scientific outputs were preserved.

Preservation baselines rechecked unchanged before handoff:

- Current manuscript.tex: fb1636c78476b9e9e136d3e1acacacb1fcca2a4664c859d9261e9b82baf8c75b
- Old manuscript.tex: fe76c3956ba1242cd658ba5ca6faebf149d796b659f5f365b7fc96b28413e92e
- Old references.bib: 7ded1b2fcad435d61d93e55d0f55c87525f69bef1967a745261f40f56c85cdbc
- Stage 6 novelty audit: cc1cab16565106f4c035639726feba98f1027521a907d3af3d0998ed0f1bdbb1
- Stage 6 reference verification: 2577763616a90b70ff43f9219b3a159c4d67146bf9517b8168bc62e2cb9320ff
- HEAD: fee20c316040c57b69ba12a193530c955b539771

Tracked and staged Git diffs remain empty. The manuscript directory and scientific output directories already contained untracked user artifacts; this is not represented as a clean-worktree assertion. All 36 generated bibliography items were counted and generated braces balance. The nine new DOI entries were checked against fresh deposits, with the explicitly documented TimeTrack name-segmentation and Qu subtitle/date exceptions resolved from primary records; the book uses the publisher's preferred citation.

No Introduction, Related Work or Discussion was written. Stage 6A can pass without clearing Stage 6's separate scientific novelty gate.

