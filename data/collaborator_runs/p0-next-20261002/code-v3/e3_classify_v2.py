"""One documented prompt iteration, independent v2 seed menu; unchanged rule."""
import e3_classify

SYSTEM_V2 = (
    'Classify ONE anonymous observed transport contact as feint or real using '
    'only its supplied position and movement history. The protected port is '
    'at Cartesian coordinates (1,18). A real threat tends toward this port; '
    'a feint tends to hold or drift without portward intent. '
    'Movement is stochastic and obstacles may cause a real threat to pause '
    'or make a lateral/away step, so do NOT require every observed step to '
    'close monotonically. Evaluate the overall portward tendency over ALL '
    'supplied observations, not just the last step. '
    'For clarity, the portward projection of mean observed delta is '
    'mean(dx)*(1-last_x)+mean(dy)*(18-last_y). Positive overall tendency '
    'is evidence for real even when some individual steps are lateral. '
    'A local grid may show OTHER contacts; do not transfer their roles to '
    'the anonymous contact. IDs and role labels are not supplied. '
    'Use equal class priors. Give p_real as your probability of real, not '
    'a generic confidence score for whichever label you chose. '
    'Return only JSON {"label":"real" or "feint","p_real":number}. '
    'label must be real iff p_real>0.5, otherwise feint.'
)


if __name__=='__main__':
    e3_classify.SYSTEM=SYSTEM_V2
    e3_classify.main()
