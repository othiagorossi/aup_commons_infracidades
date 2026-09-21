df <- read.csv("data/sustainability_scores_all_reps.csv", stringsAsFactors = FALSE)

order_levels <- c("no_protection", "weak_protection", "moderate_protection",
                  "strong_protection", "maximum_protection")
df$policy_scenario <- factor(df$policy_scenario, levels = order_levels)

metrics <- c("overall_sustainability", "social_sustainability",
             "economic_sustainability", "final_farmers_pct",
             "land_appreciation_pct", "mean_displacement_rate")
n <- nrow(df)
k <- length(order_levels)

safe_shapiro_p <- function(x) {
  if (length(unique(x)) < 2L) return(NA_real_)
  tryCatch(shapiro.test(x)$p.value, error = function(e) NA_real_)
}

shapiro_grid <- sapply(metrics, function(m)
  sapply(order_levels, function(lv)
    safe_shapiro_p(df[df$policy_scenario == lv, m])))

shapiro_min_p <- apply(shapiro_grid, 2, function(v)
  ifelse(all(is.na(v)), NA_real_, min(v, na.rm = TRUE)))
n_zero_var <- colSums(is.na(shapiro_grid))

levene_median_p <- function(values, groups) {
  z <- abs(values - ave(values, groups, FUN = median))
  tryCatch(anova(lm(z ~ factor(groups)))$"Pr(>F)"[1],
           error = function(e) NA_real_)
}
levene_p <- sapply(metrics, function(m) levene_median_p(df[[m]], df$policy_scenario))

assumptions <- data.frame(metric = metrics,
                          min_shapiro_p = round(shapiro_min_p, 4),
                          levene_p = round(levene_p, 4),
                          grupos_variancia_nula = n_zero_var)
write.csv(assumptions, "outputs/tables/assumptions_A.csv", row.names = FALSE)
print(assumptions)

kw <- do.call(rbind, lapply(metrics, function(m) {
  kt <- kruskal.test(df[[m]] ~ df$policy_scenario)
  data.frame(metric = m,
             H = round(unname(kt$statistic), 2),
             p = signif(kt$p.value, 3),
             epsilon2 = round((unname(kt$statistic) - k + 1) / (n - k), 3))
}))
write.csv(kw, "outputs/tables/kruskal_wallis_A.csv", row.names = FALSE)
print(kw)

posthoc_holm <- function(metric_name) {
  prs <- combn(order_levels, 2, simplify = FALSE)
  out <- do.call(rbind, lapply(prs, function(p) {
    x <- df[[metric_name]][df$policy_scenario == p[1]]
    y <- df[[metric_name]][df$policy_scenario == p[2]]
    wt <- wilcox.test(x, y)
    U_x <- unname(wt$statistic) - length(x) * (length(x) + 1) / 2
    data.frame(contrast = paste(p, collapse = " vs "),
               p_raw = signif(wt$p.value, 3),
               rank_biserial = round(1 - 2 * U_x / (length(x) * length(y)), 3))
  }))
  out$p_holm <- signif(p.adjust(out$p_raw, method = "holm"), 3)
  out[order(out$contrast), ]
}

ph_overall  <- posthoc_holm("overall_sustainability")
ph_retention <- posthoc_holm("final_farmers_pct")
write.csv(ph_overall,   "outputs/tables/posthoc_overall_A.csv",  row.names = FALSE)
write.csv(ph_retention, "outputs/tables/posthoc_retention_A.csv", row.names = FALSE)
print(ph_overall)

gm <- aggregate(cbind(final_farmers_pct, land_appreciation_pct,
                      protection_index) ~ policy_scenario, data = df, FUN = mean)
gm <- gm[match(order_levels, gm$policy_scenario), ]

rho_ret <- cor.test(gm$protection_index, gm$final_farmers_pct,
                    method = "spearman", exact = FALSE)
rho_apr <- cor.test(gm$protection_index, log(gm$land_appreciation_pct),
                    method = "spearman", exact = FALSE)
r_eq    <- cor.test(df$social_sustainability, df$economic_sustainability,
                    method = "pearson")
rho_eq  <- cor.test(df$social_sustainability, df$economic_sustainability,
                    method = "spearman", exact = FALSE)

associations <- data.frame(
  associacao = c("Protecao x retencao", "Protecao x log(apreciacao)",
                 "Social x economica (Pearson)", "Social x economica (Spearman)"),
  estatistica = c("rho", "rho", "r", "rho"),
  valor = round(c(unname(rho_ret$estimate), unname(rho_apr$estimate),
                  unname(r_eq$estimate), unname(rho_eq$estimate)), 3),
  p = signif(c(rho_ret$p.value, rho_apr$p.value, r_eq$p.value, rho_eq$p.value), 3))
write.csv(associations, "outputs/tables/associations_A.csv", row.names = FALSE)
print(associations)

cat("\nConcluído. Tabelas em outputs/tables/\n")