pragma circom 2.0.0;

// circomlib's comparator templates turn integer comparisons into constraints.
// The library path is supplied by setup.sh, so this import resolves from the
// locally pinned circomlib package rather than an unversioned global install.
include "circomlib/circuits/comparators.circom";

/**
 * Proves that the private birthYear is at least MINIMUM_AGE calendar years
 * before the public currentYear.
 *
 * SECURITY NOTES
 * - birthYear is private because it is intentionally omitted from main's
 *   public-input list.
 * - currentYear is public and must also be checked by the verifier against its
 *   own clock. A proof only establishes statements about its public inputs.
 * - isEligible is an output, and Circom outputs are public signals.
 * - Num2Bits prevents field wraparound from turning a negative age into a very
 *   large positive field element.
 */
template AgeCheck(nBits) {
    signal input birthYear;
    signal input currentYear;
    signal output isEligible;

    // Explicit range constraints make both years canonical n-bit integers.
    component birthYearRange = Num2Bits(nBits);
    component currentYearRange = Num2Bits(nBits);
    birthYearRange.in <== birthYear;
    currentYearRange.in <== currentYear;

    // This is the private intermediate value requested by the specification.
    signal ageInYears;
    ageInYears <== currentYear - birthYear;

    // Constrain the subtraction result to a non-negative n-bit integer. If
    // birthYear is later than currentYear, finite-field wraparound cannot fit
    // into nBits and the witness is rejected.
    component ageRange = Num2Bits(nBits);
    ageRange.in <== ageInYears;

    // Mathematically constrain currentYear - birthYear >= 18.
    component atLeastEighteen = GreaterEqThan(nBits);
    atLeastEighteen.in[0] <== ageInYears;
    atLeastEighteen.in[1] <== 18;
    isEligible <== atLeastEighteen.out;

    // Do not merely reveal a Boolean result: require the eligible branch. This
    // prevents a valid proof with public isEligible = 0 from being accepted by
    // an integration that accidentally forgets to check the output.
    isEligible === 1;
}

// 16 bits comfortably covers four-digit years while keeping the comparator
// compact. Outputs are public automatically; currentYear is the sole public
// input. SnarkJS emits publicSignals as [isEligible, currentYear].
component main { public [currentYear] } = AgeCheck(16);

