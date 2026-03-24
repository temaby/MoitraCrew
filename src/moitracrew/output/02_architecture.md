## Technical Specification: Account Management Feature - Create/Edit/Delete Functionality

### 1. Technology Stack with Justification

The existing technology stack will be fully utilized for implementing the account create/edit/delete functionality. This approach ensures consistency with the current codebase, leverages established patterns, and minimizes the introduction of new dependencies or learning curves for the development team.

*   **Backend**: C#, ASP.NET Core 8.0
    *   **Justification**: This is the existing backend framework, providing robust API capabilities, performance, and a strong type system.
*   **Database**: Microsoft SQL Server
    *   **Justification**: The existing persistent storage for the application.
*   **ORM**: Entity Framework Core 8.0.11
    *   **Justification**: The established ORM for interacting with the database, simplifying data operations and migrations.
*   **Backend Libraries**: AutoMapper, Serilog, Swashbuckle.AspNetCore
    *   **Justification**: These are integral parts of the existing backend for object mapping, logging, and API documentation, respectively.
*   **Frontend**: TypeScript, React
    *   **Justification**: The existing frontend framework, offering component-based development and static type checking for a maintainable UI.
*   **Frontend Libraries**: Ant Design, @reduxjs/toolkit, react-redux, react-router-dom, moment
    *   **Justification**: Ant Design provides a comprehensive UI component library, ensuring a consistent user experience. Redux Toolkit is used for state management, maintaining a predictable data flow. React Router handles client-side navigation.

### 2. Data Models with Field Types

The existing `Account` entity and associated Data Transfer Objects (DTOs) will be largely reused. A minor modification to `AccountCreateDTO` is proposed to accommodate an "Initial Balance" if required, and a `Currency` DTO will be needed for the frontend.

#### 2.1. Backend Data Models (`inex.Data/Models/`)

*   **`Account.cs`** (Existing)
    ```csharp
    public class Account : NamedEntity // Inherits Id (int), Name (string), CreatedBy (int?), CreatedOn (DateTime), UpdatedBy (int?), UpdatedOn (DateTime?)
    {
        // Id, Name, CreatedBy, CreatedOn, UpdatedBy, UpdatedOn inherited
        public int UserId { get; set; } // Foreign key to User
        public int CurrencyId { get; set; } // Foreign key to Currency
        public bool IsEnabled { get; set; } // Indicates if the account is active

        public User User { get; set; } = null!;
        public Currency Currency { get; set; } = null!;

        public ICollection<Transaction> Transactions { get; } = new List<Transaction>();
    }
    ```

*   **`Currency.cs`** (Existing, used for selection in UI)
    ```csharp
    public class Currency : NamedEntity // Inherits Id (int), Name (string)
    {
        // Additional currency-specific fields might exist (e.g., Symbol, Code)
        public string Code { get; set; } = null!; // e.g., "USD", "EUR"
        public string Symbol { get; set; } = null!; // e.g., "$", "€"
        // ... potentially other fields like IsBaseCurrency, DisplayOrder
    }
    ```
    *Note: The actual `Currency.cs` in `inex.Data/Models/` will dictate the exact fields.*

#### 2.2. Backend Data Transfer Objects (DTOs) (`inex.Services/Models/Records/Account/`)

*   **`AccountCreateDTO.cs`** (Modified)
    ```csharp
    public record AccountCreateDTO : NamedDTO // Inherits Name (string)
    {
        // Name inherited
        public int CurrencyId { get; init; }
        public bool IsEnabled { get; init; } = true; // Default to true for new accounts
        public decimal? InitialBalance { get; init; } // Optional: For initial transaction upon creation
    }
    ```
    *   **Justification for `InitialBalance`**: Addresses US-001. Instead of storing balance directly on `Account` (which is a derived value from `Transactions`), an initial transaction will be created for the specified amount when the account is first created.

*   **`AccountUpdateDTO.cs`** (Existing)
    ```csharp
    public record AccountUpdateDTO : NamedDTO // Inherits Name (string)
    {
        public int Id { get; init; }
        // Name inherited
        public int CurrencyId { get; init; }
        public bool IsEnabled { get; init; }
    }
    ```

*   **`AccountDetailsDTO.cs`** (Existing)
    ```csharp
    public record AccountDetailsDTO : ResponseDTO // Inherits Id (int)
    {
        // Id inherited
        public string Name { get; init; } = null!;
        public int CurrencyId { get; init; }
        public string CurrencyName { get; init; } = null!;
        public string CurrencyCode { get; init; } = null!;
        public bool IsEnabled { get; init; }
        // Potentially a `CurrentBalance` if derived and added to DTO mapping in AutoMapper for display purposes
    }
    ```

*   **`CurrencyDetailsDTO.cs`** (New - for fetching currency options for UI)
    ```csharp
    public record CurrencyDetailsDTO : NamedDTO // Inherits Name (string)
    {
        public int Id { get; init; }
        public string Code { get; init; } = null!;
        public string Symbol { get; init; } = null!;
    }
    ```
    *   **Justification**: The frontend needs a list of available currencies (ID, name, code, symbol) to populate the currency selection dropdown in the account creation/edit forms.

#### 2.3. Frontend Data Models (`inex/ClientApp/src/model/`)

*   **`Account/AccountDetails.ts`** (Existing)
    ```typescript
    export interface AccountDetails {
        id: number;
        name: string;
        currencyId: number;
        currencyName: string;
        currencyCode: string;
        isEnabled: boolean;
        // Potentially `currentBalance?: number;` if added to backend DTO
    }
    ```

*   **`Account/AccountCreateState.ts`** (New - for form input)
    ```typescript
    export interface AccountCreateState {
        name: string;
        currencyId: number;
        isEnabled: boolean;
        initialBalance?: number; // Optional initial balance for new accounts
    }
    ```

*   **`Account/AccountEditState.ts`** (New - for form input)
    ```typescript
    export interface AccountEditState {
        id: number;
        name: string;
        currencyId: number;
        isEnabled: boolean;
    }
    ```

*   **`Currency/CurrencyDetails.ts`** (New - for currency selection)
    ```typescript
    export interface CurrencyDetails {
        id: number;
        name: string;
        code: string;
        symbol: string;
    }
    ```

### 3. API Contract

The existing `AccountsController` already provides all the necessary endpoints. A new endpoint for fetching currencies will be added.

#### 3.1. Existing Accounts API Endpoints (`inex/Controllers/AccountsController.cs`)

*   **`POST api/accounts` - Create Account (US-001)**
    *   **Request**: `AccountCreateDTO`
        ```json
        {
            "name": "New Savings Account",
            "currencyId": 1, // e.g., ID for USD
            "isEnabled": true,
            "initialBalance": 1000.50 // Optional
        }
        ```
    *   **Response**: `ResponseCreateDTO`
        ```json
        {
            "id": 5 // ID of the newly created account
        }
        ```
    *   **Behavior**: The `AccountService.CreateAsync` method will be updated to, if `InitialBalance` is provided, create a new `Transaction` of type `INCOME` linked to the new account with the specified amount and current date.

*   **`PUT api/accounts/{id}` - Update Account (US-002)**
    *   **Request**: `AccountUpdateDTO`
        ```json
        {
            "id": 5,
            "name": "Updated Savings Account",
            "currencyId": 2, // e.g., ID for EUR
            "isEnabled": false
        }
        ```
    *   **Response**: `AccountDetailsDTO`
        ```json
        {
            "id": 5,
            "name": "Updated Savings Account",
            "currencyId": 2,
            "currencyName": "Euro",
            "currencyCode": "EUR",
            "isEnabled": false
            // "currentBalance": 1000.50 (if derived)
        }
        ```

*   **`DELETE api/accounts/{id}` - Delete Single Account (US-003)**
    *   **Request**: (URL parameter `id`)
    *   **Response**: `200 OK` (No content)
    *   **Security/Integrity**: The backend `AccountService.DeleteAsync` method should include a check to prevent deletion of accounts with associated transactions, or a soft-delete mechanism (e.g., setting `IsEnabled = false`) should be used. *Current behavior in `AccountService.cs` implies hard delete via `DbInEx.AccountRepository.Delete` which, if EF Core is configured for cascade deletes, will also remove related transactions. This should be explicitly reviewed and documented, potentially changing to soft delete or adding a warning.* For this feature, we will proceed with the current hard-delete assumption with a confirmation dialog on the frontend.

*   **`DELETE api/accounts?ids=id1,id2,...` - Bulk Delete Accounts (US-004)**
    *   **Request**: (URL query parameter `ids` with comma-separated IDs)
    *   **Response**: `200 OK` (No content)
    *   **Behavior**: Similar integrity checks as single delete apply.

*   **`GET api/accounts` - Get All Accounts (Existing)**
    *   **Request**: (Optional query parameter `mode` for `ALL`, `ACTIVE`, `INACTIVE`)
    *   **Response**: `ResponseDataDTO<AccountDetailsDTO>`

#### 3.2. New Currencies API Endpoint (`inex/Controllers/CurrenciesController.cs`)

*   **`GET api/currencies` - Get All Currencies**
    *   **Request**: None
    *   **Response**: `ResponseDataDTO<CurrencyDetailsDTO>`
        ```json
        {
            "data": [
                {
                    "id": 1,
                    "name": "US Dollar",
                    "code": "USD",
                    "symbol": "$"
                },
                {
                    "id": 2,
                    "name": "Euro",
                    "code": "EUR",
                    "symbol": "€"
                }
                // ... more currencies
            ],
            "pagination": null
        }
        ```
    *   **Justification**: Provides the necessary data for the currency selection dropdown in the frontend forms.
    *   **Implementation**: A new `CurrenciesController.cs` and `CurrencyService.cs` will be created, leveraging `inex.Data.Models.Currency` and `IInExUnitOfWork`.

### 4. Component/Module Breakdown with Responsibilities

#### 4.1. Backend (`inex/`, `inex.Services/`, `inex.Data/`)

*   **`inex.Data/Models/Account.cs`**
    *   **Responsibility**: Defines the structure of an account in the database.
*   **`inex.Data/Models/Currency.cs`**
    *   **Responsibility**: Defines the structure of a currency in the database.
*   **`inex.Data/Repositories/Base/Repository.cs`** / **`IEditableRepository.cs`**
    *   **Responsibility**: Provide generic data access methods for `Account` and `Currency` entities.
*   **`inex.Data/Repositories/InExUnitOfWork.cs`**
    *   **Responsibility**: Orchestrates transactions and access to various repositories.
*   **`inex.Services/Models/Records/Account/AccountCreateDTO.cs`** (Modified)
    *   **Responsibility**: Data contract for creating accounts, now including `InitialBalance`.
*   **`inex.Services/Models/Records/Currency/CurrencyDetailsDTO.cs`** (New)
    *   **Responsibility**: Data contract for exposing currency details to the frontend.
*   **`inex.Services/Services/Base/IAccountService.cs`** / **`AccountService.cs`** (Modified)
    *   **Responsibility**: Implements business logic for account management. `CreateAsync` will be updated to handle `InitialBalance` by creating a `Transaction`. The `DeleteAsync` methods should be reviewed for data integrity regarding existing transactions.
*   **`inex.Services/Services/Base/ICurrencyService.cs`** / **`CurrencyService.cs`** (New)
    *   **Responsibility**: Provides business logic for retrieving currency data.
*   **`inex/Controllers/AccountsController.cs`** (Existing)
    *   **Responsibility**: Exposes RESTful endpoints for account CRUD operations. No changes needed to method signatures, but `AccountCreateDTO` definition changes.
*   **`inex/Controllers/CurrenciesController.cs`** (New)
    *   **Responsibility**: Exposes a RESTful endpoint `GET api/currencies` to retrieve available currencies for the frontend.

#### 4.2. Frontend (`inex/ClientApp/`)

*   **`src/model/Account/AccountCreateState.ts`** (New)
    *   **Responsibility**: Defines the interface for account creation form data.
*   **`src/model/Account/AccountEditState.ts`** (New)
    *   **Responsibility**: Defines the interface for account editing form data.
*   **`src/model/Currency/CurrencyDetails.ts`** (New)
    *   **Responsibility**: Defines the interface for currency data received from the backend.
*   **`src/store/index.ts`**
    *   **Responsibility**: Root Redux store configuration.
*   **`src/store/accounts/accounts-slice.ts`** (Modified)
    *   **Responsibility**: Manages the state for accounts. Will include new reducers for `addAccount`, `updateAccount`, `deleteAccount`, `setAccountsLoading`, `setAccountsError`.
*   **`src/store/accounts/accounts-actions.ts`** (Modified)
    *   **Responsibility**: Defines Redux actions and thunks for interacting with the `AccountsController` API. New thunks: `createAccount`, `updateAccount`, `deleteAccount`, `bulkDeleteAccounts`, and potentially `fetchCurrencies` (or `fetchCurrencies` could go into its own slice if it becomes complex).
*   **`src/store/currencies/currencies-slice.ts`** (New)
    *   **Responsibility**: Manages the state for available currencies.
*   **`src/store/currencies/currencies-actions.ts`** (New)
    *   **Responsibility**: Defines Redux actions and thunks for fetching currency data from `CurrenciesController`.
*   **`src/components/Accounts/AccountForm.tsx`** (New)
    *   **Responsibility**: Reusable Ant Design form component for both creating and editing accounts.
        *   Takes `AccountCreateState` or `AccountEditState` as props (or a combined interface).
        *   Includes input fields for `Name`, `CurrencyId` (Ant Design `Select` with options from `CurrencyDetails`), `IsEnabled` (Ant Design `Switch`).
        *   Includes `initialBalance` field only for creation mode.
        *   Handles form validation using Ant Design's form capabilities.
        *   Emits `onSubmit` event with form data.
*   **`src/pages/Accounts.tsx`** (Modified)
    *   **Responsibility**: Displays the list of accounts.
        *   Integrate `AccountForm` into the existing Ant Design `Drawer`.
        *   Add "Edit" and "Delete" actions (e.g., Ant Design `Dropdown` or `Popconfirm`) to each row in the accounts `Table`.
        *   Implement multi-select checkboxes for bulk delete (Ant Design `Table` row selection).
        *   Display a "Delete Selected" button when accounts are selected.
        *   Dispatch Redux actions (e.g., `createAccount`, `updateAccount`, `deleteAccount`, `bulkDeleteAccounts`) upon form submission or action confirmation.
        *   Display Ant Design `message` or `notification` for success/error feedback.
        *   Fetch currencies (`fetchCurrencies`) on component mount for form dropdowns.

### 5. Folder Structure

The new files will follow the established project structure.

#### 5.1. Backend (`inex.Services/Models/Records/`, `inex.Services/Services/`, `inex/Controllers/`)

```
inex.Services/
├── Models/
│   ├── Records/
│   │   ├── Account/
│   │   │   └── AccountCreateDTO.cs (modified)
│   │   └── Currency/
│   │       └── CurrencyDetailsDTO.cs (new)
│   └── ConfigProfiles/
│       └── CurrencyProfile.cs (new, for AutoMapper)
├── Services/
│   ├── Base/
│   │   └── ICurrencyService.cs (new)
│   ├── AccountService.cs (modified for InitialBalance and delete behavior review)
│   └── CurrencyService.cs (new)
inex/
└── Controllers/
    ├── AccountsController.cs (no code changes, but behavior changes to reflect DTO modification)
    └── CurrenciesController.cs (new)
```

#### 5.2. Frontend (`inex/ClientApp/src/`)

```
inex/ClientApp/src/
├── components/
│   └── Accounts/
│       └── AccountForm.tsx (new)
├── model/
│   ├── Account/
│   │   ├── AccountCreateState.ts (new)
│   │   ├── AccountEditState.ts (new)
│   │   └── AccountDetails.ts (existing)
│   └── Currency/
│       └── CurrencyDetails.ts (new)
├── pages/
│   └── Accounts.tsx (modified)
└── store/
    ├── accounts/
    │   ├── accounts-actions.ts (modified)
    │   └── accounts-slice.ts (modified)
    └── currencies/ (new folder)
        ├── currencies-actions.ts (new)
        └── currencies-slice.ts (new)
```

### 6. Implementation Guidelines and Constraints for the Developer

1.  **Backend (`inex.Services`, `inex.Data`, `inex` projects)**:
    *   **AutoMapper**: Ensure `AccountCreateDTO` and `AccountUpdateDTO` are correctly mapped to `Account` entities. A new `CurrencyProfile.cs` will be needed for `Currency` to `CurrencyDetailsDTO` mapping.
    *   **Account Service `CreateAsync`**:
        *   When `AccountCreateDTO.InitialBalance` is provided and is greater than 0, create a new `Transaction` entity.
        *   The `Transaction` should be of `TransactionType.INCOME`, linked to the newly created `Account`, with `Value = InitialBalance`, and `TransactionDate = DateTime.UtcNow`.
        *   This transaction should be saved within the same `UnitOfWork` as the account creation to ensure atomicity.
    *   **Account Service `DeleteAsync`**:
        *   **CRITICAL REVIEW**: Re-evaluate the current deletion strategy. If a hard delete of an `Account` implicitly cascades to `Transactions`, this needs to be explicitly confirmed and acceptable.
        *   **RECOMMENDATION**: Implement soft delete for accounts (e.g., introduce `IsDeleted` field to `Account.cs` and set it to `true` instead of physically removing the record) OR prevent deletion if there are associated transactions, prompting the user to delete transactions first. For this task, assuming no major changes to existing deletion logic, but a strong recommendation to review for production.
        *   If hard delete is maintained, ensure comprehensive unit tests cover cascade behavior.
    *   **Currency Service & Controller**: Implement `CurrencyService` to retrieve all `Currency` entities and map them to `CurrencyDetailsDTO`. Implement `CurrenciesController` with a single `GET` endpoint.
    *   **Validation**: Ensure DTOs have appropriate data annotations (`[Required]`, `[Range]`, etc.) for validation, and backend service methods handle invalid input gracefully, returning informative `BadRequest` responses.

2.  **Frontend (`inex/ClientApp` project)**:
    *   **UI/UX**: Strictly adhere to Ant Design components and design patterns for forms, tables, buttons, and notifications.
        *   Use `Drawer` for create/edit forms as seen in `Accounts.tsx`.
        *   Use `Table.rowSelection` for bulk actions.
        *   Use `Popconfirm` or `Modal.confirm` for delete confirmation dialogs.
    *   **State Management**:
        *   `Accounts.tsx` should dispatch actions to `accounts-actions.ts` for all CRUD operations.
        *   New thunks in `accounts-actions.ts` should handle API calls and then dispatch standard Redux actions to update the `accounts-slice.ts` state.
        *   Create a new Redux slice (`currencies-slice.ts`) and actions (`currencies-actions.ts`) for managing the list of available currencies. Fetch these currencies once when the `Accounts` page loads.
    *   **Forms**:
        *   `AccountForm.tsx` should be a controlled component.
        *   Implement client-side validation using Ant Design `Form` component's built-in validation rules.
        *   The `Currency` selection should use an Ant Design `Select` component populated dynamically from the `currencies-slice` state.
        *   The `IsEnabled` field should use an Ant Design `Switch` component.
        *   The `InitialBalance` field should be an Ant Design `InputNumber` and only visible when creating a new account.
    *   **Error Handling**: Display user-friendly error messages (e.g., using `message.error` or `notification.error` from Ant Design) for failed API calls or validation issues.
    *   **Data Refresh**: Ensure the account list is automatically refreshed (e.g., re-fetching accounts) after successful create, edit, or delete operations.
    *   **Loading States**: Implement loading indicators (e.g., Ant Design `Spin` or button loading states) during API calls to improve user experience.

3.  **General**:
    *   **TypeScript**: Maintain strong typing throughout the backend DTOs, service interfaces, frontend models, and React components.
    *   **Code Style**: Adhere to the existing C# and TypeScript/React coding conventions found in the repository.
    *   **Testing**: Write unit tests for new or modified backend services (`inex.Services.Tests`) and frontend components/Redux logic (using `npm test`).
    *   **Documentation**: Update relevant XML comments for backend code and add comments for complex frontend logic.