#!/usr/bin/env Rscript
# ==============================================================================
# 03_convergence_and_robustness.R
# (a) Convergência do número de replicações (protocolo C)
# (b) Robustez do gradiente de proteção a dois regimes de sucesso inicial (ABM1)
# Reproduz os números das seções 3.4 e 4.2 do artigo.
# Execução a partir da raiz do repositório:
#   Rscript analysis/03_convergence_and_robustness.R
# Dependências: base R apenas.
# ==============================================================================

# ---------------------------------------------------------------------------
# (a) Convergência
# ---------------------------------------------------------------------------
conv <- read.csv("data/convergence_check.csv", stringsAsFactors = FALSE)
conv$variacao_retencao_pct <- round(
  c(NA, diff(conv$retencao_media) / head(conv$retencao_media, -1) * 100), 2)
write.csv(conv, "outputs/tables/convergence_check_R.csv", row.names = FALSE)
print(conv)

# ---------------------------------------------------------------------------
# (b) Robustez de regimes: correlação de postos do gradiente entre MODERATE e HIGH
# ---------------------------------------------------------------------------
rob <- read.csv("data/robustness_regimes.csv", stringsAsFactors = FALSE)

order_levels <- c("no_protection", "weak_protection", "moderate_protection",
                  "strong_protection", "maximum_protection")

gm <- aggregate(cbind(final_farmers_pct, overall_sustainability,
                      land_appreciation_pct) ~ regime_abm1 + policy_scenario,
                data = rob, FUN = mean)
gm$policy_scenario <- factor(gm$policy_scenario, levels = order_levels)
gm <- gm[order(gm$regime_abm1, gm$policy_scenario), ]

by_regime <- split(gm, gm$regime_abm1)

rho_ret <- cor.test(by_regime$MODERATE$final_farmers_pct,
                    by_regime$HIGH$final_farmers_pct,
                    method = "spearman", exact = FALSE)
rho_sust <- cor.test(by_regime$MODERATE$overall_sustainability,
                     by_regime$HIGH$overall_sustainability,
                     method = "spearman", exact = FALSE)

robustness_summary <- data.frame(
  indicador = c("Retencao (%)", "Sustentabilidade geral", "Apreciacao (%)"),
  MODERATE = round(c(mean(by_regime$MODERATE$final_farmers_pct),
                     mean(by_regime$MODERATE$overall_sustainability),
                     mean(by_regime$MODERATE$land_appreciation_pct)), 1),
  HIGH = round(c(mean(by_regime$HIGH$final_farmers_pct),
                 mean(by_regime$HIGH$overall_sustainability),
                 mean(by_regime$HIGH$land_appreciation_pct)), 1))
write.csv(robustness_summary, "outputs/tables/robustness_summary.csv", row.names = FALSE)
print(robustness_summary)

rank_correlations <- data.frame(
  indicador = c("Retencao", "Sustentabilidade geral"),
  spearman_rho = round(c(unname(rho_ret$estimate), unname(rho_sust$estimate)), 3),
  p = signif(c(rho_ret$p.value, rho_sust$p.value), 3))
write.csv(rank_correlations, "outputs/tables/robustness_rank_correlations.csv",
          row.names = FALSE)
print(rank_correlations)

cat("\nConcluído. Tabelas em outputs/tables/\n")
