# Bifrost — samlet brugerrejse og dataflow

Dato: 12. juli 2026

## Mål

Bifrost skal fungere som én sammenhængende sag fra første behov til menneskelig godkendelse og drift. En medarbejder skal kunne komme sikkert igennem processen uden at kende alle lovhenvisninger på forhånd, mens en jurist fortsat skal kunne se klassifikation, prædikater, begrundelser, evidens og audit-spor.

Grundprincippet er: **Registrér en oplysning én gang, genbrug den i alle efterfølgende faser, og gør den redigerbar dér, hvor ny dokumentation kan korrigere den.**

## Den anbefalede rejse

| Fase | Brugerens opgave | Data der følger med | Stopregel | Resultat |
|---|---|---|---|---|
| 1. Intake | Beskriv behovet, opret sags-ID, vælg indkøb/udvikling og beskriv systemet | Sags-ID, behov, systemnavn, systembeskrivelse, dato og anskaffelsesform | En permanent sag oprettes først, når sags-ID'et bekræftes | Én sag med en genanvendelig grundbeskrivelse |
| 2. EU AI Act | Besvar EC-klassifikationsflowet | Sagskontekst vises; svar, flag, sprog og gennemførelsestidspunkt gemmes på sagen | Juridisk vurdering er låst, indtil klassifikationen er gennemført — også når resultatet er nul aktive flag | Dokumenteret EU-klassifikation |
| 3. Juridisk vurdering | Kontrollér den medbragte beskrivelse og EC-prædikater, kør regelmotoren | Sags-ID, beskrivelse og EU-resultat er forudfyldt | Brugeren skal aktivt gennemgå input; Bifrost træffer ikke den menneskelige beslutning | GO, BETINGET-GO eller NO-GO kobles til sagen og opdaterer workflow-status |
| 4. Risiko og evidens | Upload kontrakter, kontrollér udtrukne fakta og udfyld kun de artefakter vurderingen kræver | Systemnavn, formål og sags-ID følger med til risikovurderingen; evidens journaliseres på samme sag | Nye dokumenter må korrigere forudfyldte fakta; uafklarede forhold vises eksplicit | Gemte risikovurderinger og et målrettet evidensgrundlag |
| 5. Godkendelse og drift | Gennemgå samlet status, rapport og resterende forhold; sæt derefter menneskelig status | Klassifikation, verdict, risiko, evidens, audit-spor og rapport er samlet | NO-GO kan ikke fremstilles som klar. Endelig godkendelse foretages af en ansvarlig medarbejder/jurist | Godkendt/idriftsat sag med reviewdato og audit-spor |

## Fundne brud og overlap

| Fund før ændringen | Konsekvens | Løsning |
|---|---|---|
| Intake autosavede alle nye brugere i den samme `__draft__`-sag og kunne derefter oprette endnu en sag | Dobbeltregistrering, sammenblandede kladder og en URL, der pegede på forkert sag | Kladder gemmes lokalt, indtil brugeren bekræfter et permanent sags-ID; derefter findes præcis én backend-sag |
| En senere redigering af intake kunne overskrive EU-data i `intake_state` | Allerede udført klassifikation kunne forsvinde | Ukendte/senere fasefelter bevares ved intake-gemning |
| Procesoversigten lovede automatisk genbrug, men vurderingssiden læste kun EU-flag fra den aktuelle browsersession | Genåbnede sager skulle klassificeres igen eller kunne vurderes uden dokumenteret klassifikation | EU-svar og flag gemmes på sagen og genindlæses ved direkte adgang og genoptagelse |
| Et gyldigt EC-resultat med nul aktive flag blev behandlet som “ikke gennemført” | Brugeren blev sendt tilbage til et allerede afsluttet tjek | Gennemførelse afgøres af tidsstemplet, ikke antallet af flag |
| EC-flowets usynlige logikknuder blev vist som en tom side | Rejsen stoppede før resultatet | Routingmotoren gennemløber automatisk hub-knuder, håndterer betingede flag og viser en kontrolleret fejl ved ugyldig logik |
| Danske svar viste rå oversættelsesmarkører, og al juridisk hjælpetekst var foldet ud | Teknisk støj og høj kognitiv belastning for ikke-jurister | Markører renses; den korte forklaring vises først, mens juridisk hjælp kan foldes ud |
| En juridisk vurdering blev gemt i auditloggen, men ikke koblet til sagen | Sagen stod som kladde uden verdict, selv efter en gennemført vurdering | Vurderingsloggen kobles til sagen; GO giver `vurderet`, BETINGET-GO/NO-GO giver `remediation` |
| Risikovurderingen ignorerede `case_id` i URL'en | Systemnavn, formål og sag skulle udfyldes igen | Systemnavn, formål og sagskobling forudfyldes og kan korrigeres efter dokumentanalyse |
| Intake viste en generisk liste over ni evidensskabeloner før klassifikation og vurdering | Brugeren blev bedt om dokumentation, der måske ikke var relevant | Evidens flyttes til fase 4 og præsenteres efter klassifikation/vurdering |
| Processen sluttede reelt efter tre trin og havde ingen tydelig vej videre fra vurderingsresultatet | Risiko, evidens, godkendelse og drift fremstod som separate produkter | Én femfaset procesoversigt og tydelige “fortsæt”-handlinger binder hele sagen sammen |

## Dataejerskab

Den detaljerede feltmatrix findes i [`brugerrejse-dataflow.csv`](brugerrejse-dataflow.csv). De vigtigste ejerskabsregler er:

1. `Case.case_id` er den gennemgående nøgle og må aldrig erstattes af en fælles kladde-ID.
2. Grundoplysninger og EC-resultat bor i `Case.intake_state`, så de kan genbruges på tværs af sessioner.
3. Juridiske vurderinger, risikovurderinger og evidens beholder hver deres domænespecifikke datamodel, men kobles til samme `case_id`.
4. `Case.last_aggregate_status`, `Case.last_assessment_log_id` og `Case.status` er sagens korte, aktuelle resume; audit- og transitionstabellerne er historikken.
5. Senere faser må berige eller korrigere data, men må ikke tavst slette felter fra tidligere eller senere faser.

## To læseniveauer

- **Almindelig medarbejder:** kort opgaveforklaring, anbefalet næste handling, almindelige danske ord og progressive juridiske forklaringer.
- **Jurist/DPO:** adgang til lovgrundlag, EC-svar/flag, regelresultat, evidensstatus, dokumentudtræk, rapport og append-only audit-spor.

Begge arbejder i den samme sag. Der er derfor ikke en separat “juristversion”, som kræver genindtastning eller efterfølgende synkronisering.

## Bevidste menneskelige og eksterne trin

- Den endelige godkendelse er fortsat en menneskelig beslutning på sags-/godkendelsestavlen.
- Serviceportalens eksterne registrering er ikke erstattet af Bifrost; datoen registreres som dokumentation i intake.
- Den automatiske risikovurdering kræver en konfigureret LLM-provider. Uden den kan sagen og de forudfyldte felter stadig åbnes, men udkastet kan ikke genereres.
- Den danske EC-tekst er en hjælpeoversættelse og bør juridisk valideres mod den officielle engelske kilde, før den behandles som autoritativ ordlyd.
- Bifrost skal vise anbefalinger og sporbarhed, men må ikke fremstille et maskinresultat som den endelige juridiske afgørelse.

## Acceptkriterier

- Der oprettes ingen backend-sag, før et permanent sags-ID er bekræftet.
- Ét sags-ID giver højst én aktiv sag i rejsen.
- En gennemført EU-klassifikation kan genoptages på en anden side/session uden nye svar.
- Nul aktive EU-flag er et gyldigt, gennemført resultat.
- Juridisk vurdering er blokeret på en tilknyttet sag, indtil EU-tjekket er afsluttet.
- Vurderingsresultatet ses straks som sagens verdict og workflow-status.
- Risikovurderingen modtager systemnavn, formål og sags-ID automatisk.
- Redigering af intake efterfølgende bevarer EC-data og øvrige senere fasefelter.
- Procesoversigten viser fem faser og leder videre efter hvert resultat.
- Endelig status ændres kun ved en eksplicit menneskelig handling og registreres i audit-sporet.
