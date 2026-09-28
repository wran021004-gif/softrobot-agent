# Recovered Stage 3.24 evidence

Original local bytes recovered on 2026-09-28; no experiments or provider requests rerun. The original failed prose review and assisted continuation remain failures/assistance. SQLite snapshots contain immutable artifact bodies, requests, raw responses, candidate analyses, delivery and event histories; use Store.artifact or SQLite read-only access. Execution authorization anchors are intentionally not exported. Do not resume these finished sessions.

All artifacts named in the implementation report were found. The three complete Store snapshots (about 14 MB total) retain referenced artifact closure without a new export format. Session lock files are excluded. Backend files retain observations, predictions, sampled trajectories and effective physical/control inputs. The original reproduction helpers are retained; resume_protocol_once.py is historical evidence only.

| Original path | Bytes | SHA-256 |
|---|---:|---|
| analysis_gate_check.json | 214 | faf8d31e4668a68a32ae70ac35742f45e7e68f1e17ba9db494ffeda16bae262d |
| analysis_proof/analysis_receipt.json | 808 | 2b649e9d8c82dd85b2fa4df30d72c4c4bd0cccb3a0042fd549c4e5c1d277728a |
| analysis_proof/build_receipt.json | 760 | a06ac4596cac85a9ce927de9c8d7e16699d2c2337baa8c2a888b3aff470ce5f7 |
| analysis_proof/platform.sqlite | 1810432 | 460d1979ec8fe90bfee2389f3b81fdf8e4ff6599197fe31fe965c799cb112ded |
| analysis_proof/proof.json | 8346 | b2a9dd5658d78080f5a56501015d9d43d9ccf5fcfc8b4fc2e48d8bfc7fc6bc5b |
| deterministic/assessment.json | 5115 | 8b2b7f81787a966e42cb485114ba9bd6826be8298667855a914348c8aea47216 |
| deterministic/describe_receipt.json | 791 | ea889bf718d09a51c16103897171d5ab0526521220fc5cc0c9a7dd77746a1f32 |
| deterministic/evaluate_receipt.json | 777 | bedb0eebdd34d7e59f192a23cb689a60c7b8d39adffd9a4b5765eb228aeebaed |
| deterministic/input.json | 35180 | 3f6e2d6e9eb00e6777d58427fedacaaed3e7aa9683c0a8fdb0550a2eec383ca0 |
| deterministic/platform.sqlite | 4165632 | 49a2e02c14a71f8f00d1a18ce58018eaa3001abe91c95642825aa1d491014ae5 |
| deterministic/report.md | 2077 | 07eda769300e8d1980acc05bd518b39c2015d3cb22c6fe9d56d65f0d8342d496 |
| deterministic/report_receipt.json | 787 | cad417f5b30f8b136cb100474400ebd286ed255775b015a479298a0beeda9f66 |
| deterministic/sessions/gvs-time-tracking/executions/e643574e7a2d486e9ef6f1d7a1060e91/backend/actual_commands.json | 33960 | 05972c266fa8e3bbe7e39bcf4cd700ce8389a728f14e0b377b7b8d4b6537e57f |
| deterministic/sessions/gvs-time-tracking/executions/e643574e7a2d486e9ef6f1d7a1060e91/backend/compiled_physics.json | 11539 | 4dbcb54ce2922e501668261c835d2c89c90449fdbb59cf09f922cd0623ad6e25 |
| deterministic/sessions/gvs-time-tracking/executions/e643574e7a2d486e9ef6f1d7a1060e91/backend/control_spec.json | 41334 | 9c039b90517cdb7f27816a9640fa9d1d877b5e762288ccb0bf8bfacc72563e59 |
| deterministic/sessions/gvs-time-tracking/executions/e643574e7a2d486e9ef6f1d7a1060e91/backend/controller_observations.json | 367932 | 3731aa025a92a22b0c6d87f2a08f58c73ce98ac0a629587d394098c0edb62ce7 |
| deterministic/sessions/gvs-time-tracking/executions/e643574e7a2d486e9ef6f1d7a1060e91/backend/dynamics_execution.json | 1424 | 45a94075c4fce5870ee5c00445acbdc766dcd69871977f341a31bbb1e7f0fb1f |
| deterministic/sessions/gvs-time-tracking/executions/e643574e7a2d486e9ef6f1d7a1060e91/backend/experiment_scene.json | 53492 | 7a7780ce6a03bea9e2401bc87d0eede3a38b07bb31adc180674a91add3eefb84 |
| deterministic/sessions/gvs-time-tracking/executions/e643574e7a2d486e9ef6f1d7a1060e91/backend/experiment_spec.json | 1013 | eb0676e09bb267bd1989350fa686a70af797dc6e5aadf6c2f542a6d329f007d6 |
| deterministic/sessions/gvs-time-tracking/executions/e643574e7a2d486e9ef6f1d7a1060e91/backend/model_discretization.json | 205 | d17cc32631c87b76ef29a252a3d9f17900739ef91704956e48faa0023f0cbf99 |
| deterministic/sessions/gvs-time-tracking/executions/e643574e7a2d486e9ef6f1d7a1060e91/backend/nmpc_updates.json | 367743 | b6fbae8b834973b641f2ae8ce59d8eb92a12639005632f77cce8bdc99877c12d |
| deterministic/sessions/gvs-time-tracking/executions/e643574e7a2d486e9ef6f1d7a1060e91/backend/resolved_physics.json | 367704 | 047ccd8a34d489c0d7b61807387784d45bfa19653e091241b4092956bbb19bd8 |
| deterministic/sessions/gvs-time-tracking/executions/e643574e7a2d486e9ef6f1d7a1060e91/backend/result.json | 672231 | 73f0eec99797c75be5f857af7695093b70f2d949ea933065ea6c6524b65d19a1 |
| deterministic/sessions/gvs-time-tracking/executions/e643574e7a2d486e9ef6f1d7a1060e91/backend/robot.xml | 101777 | 14762a65f79fef6677630a5f1ca3540e4d304251cbd77e4a7a078ce6d798d20f |
| deterministic/sessions/gvs-time-tracking/executions/e643574e7a2d486e9ef6f1d7a1060e91/backend/robot_description.json | 21792 | b702b4d6a39626cdf6ce46d45f68e12f68ef086a500a31370a2a81bb8233b755 |
| deterministic/sessions/gvs-time-tracking/executions/e643574e7a2d486e9ef6f1d7a1060e91/backend/solver_configuration.json | 182 | 5e74166ac695703d25e9271dd38a2e7efb6a1b79a9610cfe7306605a7f660d14 |
| deterministic/sessions/gvs-time-tracking/executions/e643574e7a2d486e9ef6f1d7a1060e91/backend/trajectory.json.gz | 258140 | b124f1a30859ea2966941a290daef760d732a697057798c3aa0a680961760caa |
| deterministic/simulate_receipt.json | 813 | 46cbba163a494bc189c5257b8ec583bf95da99186c19ee2654fed57967b3edd7 |
| deterministic/summary.json | 46013 | 64da039b9eb6a0c9a4c741fc2e02f30cc4f8c59676a5c69ab67165d7f0d30e2b |
| deterministic/workflow.json | 338 | da557a89cc22eb14c28166980551f032278fcdefad94a7066ad4da6031dc6250 |
| deterministic.log | 3330 | 898a39f06e1621504c6031f17d2226da23352d6158d45a18def5702bfe1ebf34 |
| deterministic_tracking.png | 88158 | 1a4d9f49e0dfcdf1f2e2b46fc13af11fd779e591134284108fc3edad80dfcb7d |
| environment.json | 602 | 7513db6eb99342b5a8f199e517e310b638677dd5130c58ea5dcb372117b0f837 |
| frozen_input.json | 35180 | 3f6e2d6e9eb00e6777d58427fedacaaed3e7aa9683c0a8fdb0550a2eec383ca0 |
| implementation_report.md | 15746 | b4c7da8077cccaceba063afe9cb02115eda015127223acbf7ba70bbb0544be4a |
| launch_continuation.json | 378 | d4c60d084f27078fa843a61724e4c918109d6f5f83bd82bed1ab1c39769480d4 |
| launch_review.json | 2413 | 2bf605b933c1c3306595b759b2395139f6c81b8054be39daa234f9dc52dfaed4 |
| live/behavior_audit.json | 183519 | ad4075578f7a8f38ec6c599c51b6881d50a66e3c705aaa0d3ecca1c82380bb49 |
| live/first_stop_behavior_audit.json | 67856 | 7dcc79573470f42079402baaf1c5d2e353c21713701a536b8a76131a6da5d65d |
| live/first_stop_route_status.json | 17846 | 4402b2512b127e97035324e51ba869f9b1b98c044b47b0133b93d68f417a9549 |
| live/input.json | 39041 | 28eb939b400ea18f6769108f465dac4e2146f35d9de1e698d7e543f01460dacb |
| live/model_final.txt | 2424 | 08677bde5adfae3d43a746ae336f53d8c200c397cb935c64a3518dd7c7b62f09 |
| live/platform.sqlite | 8163328 | e03778069337b0cd1189496b534ff4eeefe781e2e86b9a796755631e5249b4b9 |
| live/prepared_context.json | 19897 | 332f6d4f84fcdfeaf9a0a32708ade2f6fbf30126aecf430fc98e2ef27268a678 |
| live/report.md | 2076 | 6f9f0c3e13befc1c312d792d12ae0ba3fdf38de6ed3da3d27bc8ceeb7f773fd0 |
| live/route_status.json | 298490 | 16ffec787b64a2f9bead7279c7faed296431f26d181985d8078a7cc322ca4828 |
| live/sessions/gvs-live-6971718592bc-0e6ec10af4ba158f/executions/842ae454986e4a41b9dbaca5a57fb40a/backend/actual_commands.json | 34053 | bc8bd9102c47b6371d2dfde030c61ce0ff0ab137097b84fc12fd38dd6d6bb2be |
| live/sessions/gvs-live-6971718592bc-0e6ec10af4ba158f/executions/842ae454986e4a41b9dbaca5a57fb40a/backend/compiled_physics.json | 11695 | 972a837804f8e5ed8f9d8e2a0d320df2dcee12148ccb55e77aeb554065501b51 |
| live/sessions/gvs-live-6971718592bc-0e6ec10af4ba158f/executions/842ae454986e4a41b9dbaca5a57fb40a/backend/control_spec.json | 41336 | dc54c8c609b6d760145e6f22748cde0d1db73d2297e04a773d1aead330261005 |
| live/sessions/gvs-live-6971718592bc-0e6ec10af4ba158f/executions/842ae454986e4a41b9dbaca5a57fb40a/backend/controller_observations.json | 362398 | 0df84626ed1563746660a3622624bf415b5837f7e13f288a6905bbf8af9fc56a |
| live/sessions/gvs-live-6971718592bc-0e6ec10af4ba158f/executions/842ae454986e4a41b9dbaca5a57fb40a/backend/dynamics_execution.json | 1424 | 45a94075c4fce5870ee5c00445acbdc766dcd69871977f341a31bbb1e7f0fb1f |
| live/sessions/gvs-live-6971718592bc-0e6ec10af4ba158f/executions/842ae454986e4a41b9dbaca5a57fb40a/backend/experiment_scene.json | 53495 | 7c19d843b21d2bd1cd62897b187833ec7c6952d4e21ba3680b9f066a1876d3e5 |
| live/sessions/gvs-live-6971718592bc-0e6ec10af4ba158f/executions/842ae454986e4a41b9dbaca5a57fb40a/backend/experiment_spec.json | 1013 | 555d6853fbcc3f728d973336f812e62c82996b5563488c13707e56eb3dd5e399 |
| live/sessions/gvs-live-6971718592bc-0e6ec10af4ba158f/executions/842ae454986e4a41b9dbaca5a57fb40a/backend/model_discretization.json | 205 | d17cc32631c87b76ef29a252a3d9f17900739ef91704956e48faa0023f0cbf99 |
| live/sessions/gvs-live-6971718592bc-0e6ec10af4ba158f/executions/842ae454986e4a41b9dbaca5a57fb40a/backend/nmpc_updates.json | 362205 | e730154869dd95bd7f3dbeb4ec1acafadc23887cbd53b1bd460908673d2cbfe4 |
| live/sessions/gvs-live-6971718592bc-0e6ec10af4ba158f/executions/842ae454986e4a41b9dbaca5a57fb40a/backend/resolved_physics.json | 360061 | 85337f81e1ab9940cc8a436e7e8564fe16ec7df964c096959122dba93cbc67b0 |
| live/sessions/gvs-live-6971718592bc-0e6ec10af4ba158f/executions/842ae454986e4a41b9dbaca5a57fb40a/backend/result.json | 672089 | 3ea4a8d4b7cf3c134723c7cd028199014aff2cda1169280e866f908110a5bd6b |
| live/sessions/gvs-live-6971718592bc-0e6ec10af4ba158f/executions/842ae454986e4a41b9dbaca5a57fb40a/backend/robot.xml | 94277 | e94f53fe5be5249ca395282838041891a76e5d3ba38a24d22caf2d8fdef27be5 |
| live/sessions/gvs-live-6971718592bc-0e6ec10af4ba158f/executions/842ae454986e4a41b9dbaca5a57fb40a/backend/robot_description.json | 21793 | 3a7e21fb507937c328cc5fd02346d1f17d12973eb81c069a3673905e3ce4ccbe |
| live/sessions/gvs-live-6971718592bc-0e6ec10af4ba158f/executions/842ae454986e4a41b9dbaca5a57fb40a/backend/solver_configuration.json | 182 | 5e74166ac695703d25e9271dd38a2e7efb6a1b79a9610cfe7306605a7f660d14 |
| live/sessions/gvs-live-6971718592bc-0e6ec10af4ba158f/executions/842ae454986e4a41b9dbaca5a57fb40a/backend/trajectory.json.gz | 256271 | bc900dc9618fea52653ecc85b2a7106ec7aa43268d494eba01832b48c89a6b6d |
| live/summary.json | 47843 | e02f3cfd68378a5f9d583fd06d8d475a3c1b5cdecfca05433fa095c8b6a735c5 |
| live/workflow.json | 1074 | 02779e161fcbf817fc750da94bb140c2fd17b620b369b879f8760f5c5f848dac |
| live.log | 6330 | f66e4aede516676b60294fc17f9e438fa4ede9bc15132a42994172a9579afccb |
| live_first_stop.log | 732 | b57f8edc5adecd25647a00b97fcc450936c423ab2489088adc1be90c7d4f1483 |
| live_input.json | 39321 | fcac318e78379a0bbd2313d1f07bd151e993139633a6932d3430c24317e928f7 |
| live_launch_check.json | 1056 | 175658017174d3f84dceb6461836283fc66adf91960ecab5e83b0a86288f54d9 |
| one_step_prediction_audit.json | 10753 | 9a187f3abda09f38b24538d9b9687f4eddd70db4268fcfc248f2ab818a291768 |
| protocol_continuation.json | 1222 | 911b063d67154c5136aa9384f410ce3f432b8532e0e8a024d8d684905f6b5cf7 |
| provider_interpretation_review.json | 5297 | bf5873dc3595690101da985cd99cf5a9f528890d42871f6a0f41f3fe8a974367 |
| resume_protocol_once.py | 3668 | 73943afe3aa07760196a25f1880618153647165b29fd8b305fb515ce9f8cd902 |
| validation_results.json | 1044 | de040ba48f0b611f44c8dc9dda038162e4b48bf5d090d3a5d2d82e6b77480099 |
| verify_candidate.py | 3084 | fce90ea27d07b38ae8aa0185652331625319b1e233ddbe475386306daac1ee47 |
