export type EmploymentType = "internship" | "new-grad";

export type Opportunity = {
  linkedinJobId: string;
  company: string;
  title: string;
  location: string;
  link: string;
  category: string;
  industries: string | null;
  employmentType: EmploymentType;
  startDate: string | null;
  firstSeenAt: string;
};
