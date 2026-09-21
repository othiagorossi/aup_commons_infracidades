fac <- read.csv("data/factorial_results.csv", stringsAsFactors = FALSE)

fac$tenure  <- as.numeric(sub("^t([0-9.]+)_s.*",  "\\1", fac$policy_scenario))
fac$subsidy <- as.numeric(sub(".*_s([0-9.]+)_z.*", "\\1", fac$policy_scenario))
fac$zoning  <- as.numeric(sub(".*_z([0-9.]+)$",   "\\1", fac$policy_scenario))

n <- nrow(fac)

main_effects <- do.call(rbind, lapply(c("tenure", "subsidy", "zoning"), function(f) {
  do.call(rbind, lapply(c("final_farmers_pct", "overall_sustainability"), function(m) {
    kt <- kruskal.test(fac[[m]] ~ fac[[f]])
    k <- length(unique(fac[[f]]))
    data.frame(fator = f, metrica = m,
               H = round(unname(kt$statistic), 2),
               p = signif(kt$p.value, 3),
               epsilon2 = round((unname(kt$statistic) - k + 1) / (n - k), 3))
  }))
}))
write.csv(main_effects, "outputs/tables/factorial_main_effects_B.csv", row.names = FALSE)
print(main_effects)

interaction_by_tenure <- do.call(rbind, lapply(sort(unique(fac$tenure)), function(t) {
  d <- fac[fac$tenure == t, ]
  a <- d$final_farmers_pct[d$subsidy == 0.0]
  b <- d$final_farmers_pct[d$subsidy == 0.30]
  wt <- wilcox.test(b, a)
  U_b <- unname(wt$statistic) - length(b) * (length(b) + 1) / 2
  data.frame(tenure = t,
             delta_retencao = round(mean(b) - mean(a), 2),
             p_mw = signif(wt$p.value, 3),
             rank_biserial = round(1 - 2 * U_b / (length(b) * length(a)), 3))
}))
write.csv(interaction_by_tenure,
          "outputs/tables/factorial_interaction_B.csv", row.names = FALSE)
print(interaction_by_tenure)

fac$ret_rank <- rank(fac$final_farmers_pct)
fit <- lm(ret_rank ~ tenure * subsidy + zoning, data = fac)
anova_rank <- anova(fit)
print(anova_rank)

anova_out <- data.frame(termino = rownames(anova_rank),
                        gl = anova_rank$Df,
                        SQ = round(anova_rank$`Sum Sq`, 1),
                        F = round(anova_rank$`F value`, 2),
                        p = signif(anova_rank$`Pr(>F)`, 3))
write.csv(anova_out, "outputs/tables/factorial_anova_ranks_B.csv", row.names = FALSE)

cat("\nConcluído. Tabelas em outputs/tables/\n")
